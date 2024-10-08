from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError
import os
import json
import random
from functools import wraps
from datetime import datetime
import requests

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yourdatabase.db'
app.config['UPLOAD_FOLDER'] = 'static/profile_pics'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secret-key')

# Initialize Flask-Mail and its configuration
app.config.update(
    MAIL_SERVER='sandbox.smtp.mailtrap.io',
    MAIL_PORT=587,
    MAIL_USERNAME='88daee7f3f0488',
    MAIL_PASSWORD='5c5f49fa3be358',
    MAIL_USE_TLS=True,
    MAIL_USE_SSL=False,
    MAIL_DEFAULT_SENDER='88daee7f3f0488' 
)
mail = Mail(app)

FAST2SMS_API_KEY = 'ZK6546Kod3VutrUdpxrhD2tqCQK3borO0FSvEyoSU0jGLdXjSCGIujSHChK2'

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Serializer for generating password reset tokens
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# User Model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    profile_picture = db.Column(db.String(150), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    social_media_links = db.Column(db.JSON, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    wallet_balance = db.Column(db.Float, default=0.0)
    upi_id = db.Column(db.String(100), nullable=True)  # Added UPI ID field
    phone_number = db.Column(db.String(15), unique=True,nullable=False)


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Match Registration Model
class MatchRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    game = db.Column(db.String(100), nullable=False)

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # e.g., 'upcoming', 'ongoing', 'old'

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)  # 'deposit' or 'withdrawal'
    status = db.Column(db.String(50), default='pending')  # 'pending', 'completed', 'failed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))

# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Admin-specific decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template('index.html')

# Your send_otp function using Fast2SMS
def send_otp(phone_number, otp):
    url = "https://www.fast2sms.com/dev/bulkV2"
    querystring = {
        "authorization": FAST2SMS_API_KEY,  # Replace with your Fast2SMS API key
        "variables_values": otp,  # The OTP to be sent
        "route": "otp",  # OTP route as per Fast2SMS documentation
        "numbers": phone_number  # Recipient phone number
    }
    headers = {
        'cache-control': "no-cache"
    }

    response = requests.get(url, headers=headers, params=querystring)

    # Check if the response was successful
    if response.status_code == 200:
        response_json = response.json()
        if response_json.get('return') == True:  # Check response status
            return True
        else:
            print("Error sending OTP:", response_json.get('message'))
            return False
    else:
        print("Error:", response.status_code, response.text)  # Print error details for debugging
        return False

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    otp_sent = False
    if request.method == 'POST':
        action = request.form['action']
        username = request.form['username']
        email = request.form['email']
        phone_number = request.form['phone_number']
        password = request.form['password']

        if action == 'Send OTP':
            if len(phone_number) == 10 and phone_number.isdigit():  # Validate Indian phone number
                otp = str(random.randint(1000, 9999))  # Generate a random 4-digit OTP
                session['otp'] = otp  # Store OTP in session
                session['phone_number'] = phone_number  # Store phone number in session
                if send_otp(phone_number, otp):  # Use send_otp function to send OTP
                    otp_sent = True
                    flash('OTP sent to your phone number!', 'info')
                else:
                    flash('Failed to send OTP. Please try again.', 'danger')
            else:
                flash('Invalid phone number. Please enter a valid 10-digit phone number.', 'danger')

        elif action == 'Verify OTP':
            entered_otp = request.form['otp']
            if entered_otp == session.get('otp'):
                phone_number = session.get('phone_number')
                if not phone_number:
                    flash('No phone number found in session. Please start again.', 'danger')
                    return redirect(url_for('register'))
                try:
                    existing_user = User.query.filter_by(phone_number=phone_number).first()
                    if existing_user:
                        flash('Phone number already registered!', 'danger')
                        otp_sent = True
                    else:
                        new_user = User(username=username, email=email, phone_number=phone_number)
                        new_user.set_password(password)
                        db.session.add(new_user)
                        db.session.commit()
                        session.pop('otp', None)  # Clear OTP from session
                        session.pop('phone_number', None)  # Clear phone number from session
                        flash('Registration successful!', 'success')
                        return redirect(url_for('login'))
                except IntegrityError:
                    db.session.rollback()  # Rollback the session to clear any changes
                    flash('Error: Phone number already registered!', 'danger')
                    otp_sent = True  # Keep the OTP sent flag true so the form is displayed correctly
            else:
                flash('Invalid OTP!', 'danger')
                otp_sent = True

    return render_template('register.html', otp_sent=otp_sent)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')

    return render_template('login.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            token = serializer.dumps(email, salt='password-reset-salt')
            reset_url = url_for('reset_password', token=token, _external=True)
            msg = Message('Password Reset Request', sender='your-email@example.com', recipients=[email])
            msg.body = f'Please click the following link to reset your password: {reset_url}'
            mail.send(msg)
            flash('Password reset link sent to your email.', 'info')
        else:
            flash('Email not found.', 'danger')
        return redirect(url_for('login'))

    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except SignatureExpired:
        flash('The link has expired. Please try again.', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(password)
            db.session.commit()
            flash('Your password has been updated!', 'success')
            return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/update_profile', methods=['GET'])
@login_required
def update_profile_page():
    return render_template('update_profile_page.html', user=current_user)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    user = current_user

    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            user.profile_picture = filename

    user.bio = request.form.get('bio')
    social_media_links = request.form.get('social_media_links')
    if social_media_links:
        user.social_media_links = json.loads(social_media_links)
    
    # Update UPI ID if provided
    upi_id = request.form.get('upi_id')
    if upi_id:
        user.upi_id = upi_id

    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']

        user = current_user

        if user.check_password(current_password):
            user.set_password(new_password)
            db.session.commit()
            flash('Password updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Current password is incorrect.', 'danger')

    return render_template('change_password.html')

@app.route('/wallet', methods=['GET', 'POST'])
@login_required
def wallet():
    if request.method == 'POST':
        amount = float(request.form['amount'])
        transaction_type = request.form['transaction_type']

        if current_user.wallet_balance is None:
            current_user.wallet_balance = 0.0

        if transaction_type == 'deposit':
            if amount <= 0:
                flash('Amount must be greater than zero.', 'danger')
                return redirect(url_for('wallet'))

            # Create a new transaction record for the deposit
            new_transaction = Transaction(user_id=current_user.id, amount=amount, transaction_type='deposit', status='pending')
            db.session.add(new_transaction)
            db.session.commit()
            print(f"Transaction created: {new_transaction}") 
            # Generate UPI payment URL
            upi_id_1 = "8006199683@ybl"  # Replace with your UPI ID
            upi_url = f'upi://pay?pa={upi_id_1}&pn=YourName&mc=0000&tid=000000000000&tt=123&am={amount}&cu=INR&url='

            # Redirect to the UPI payment app
            return redirect(upi_url)

        elif transaction_type == 'withdrawal':
            if amount <= 0:
                flash('Amount must be greater than zero.', 'danger')
                return redirect(url_for('wallet'))

            if current_user.wallet_balance >= amount:
                # Create a new transaction record for the withdrawal
                new_transaction = Transaction(user_id=current_user.id, amount=amount, transaction_type='withdrawal', status='pending')
                db.session.add(new_transaction)
                db.session.commit()
                flash('Withdrawal request submitted. Awaiting admin approval.', 'success')
            else:
                flash('Insufficient balance!', 'danger')

        return redirect(url_for('wallet'))

    return render_template('dashboard.html', user=current_user, balance=current_user.wallet_balance)




@app.route('/confirm_payment', methods=['POST'])
def confirm_payment():
    # Extract necessary data from the request (e.g., transaction_id, payment_status)
    transaction_id = request.form.get('transaction_id')
    payment_status = request.form.get('payment_status')

    transaction = Transaction.query.filter_by(id=transaction_id).first()
    
    if transaction and payment_status == 'success':
        # Update the transaction and user's wallet balance
        transaction.transaction_type = 'completed'
        current_user.wallet_balance += transaction.amount
        db.session.commit()
        flash('Payment successful and wallet updated!', 'success')
    else:
        flash('Payment verification failed or not completed.', 'danger')

    return redirect(url_for('wallet'))



@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Quick Match Registration Route
@app.route('/quick_join', methods=['GET', 'POST'])
def quick_join():
    if request.method == 'POST':
        username = request.form['username']
        phone = request.form['phone']
        email = request.form['email']
        game = request.form['game']

        new_registration = MatchRegistration(username=username, phone=phone, email=email, game=game)
        db.session.add(new_registration)
        db.session.commit()

        flash('You have successfully joined the match!', 'success')
        return redirect(url_for('index'))

    return render_template('quick_join.html')

# Admin Login
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'password':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('admin/login.html')

# Admin Dashboard
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    users = User.query.all()
    registrations = MatchRegistration.query.all()
    return render_template('admin/dashboard.html', users=users, registrations=registrations)

@app.route('/admin/delete_registration/<int:id>', methods=['POST'])
@admin_required
def delete_registration(id):
    registration = MatchRegistration.query.get_or_404(id)
    db.session.delete(registration)
    db.session.commit()
    flash('Registration deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

# Admin Match Management Routes
@app.route('/admin/manage_matches', methods=['GET', 'POST'])
@admin_required
def manage_matches():
    matches = Match.query.all()
    return render_template('admin/manage_matches.html', matches=matches)

@app.route('/admin/add_match', methods=['GET', 'POST'])
@admin_required
def add_match():
    if request.method == 'POST':
        title = request.form['title']
        date_str = request.form['date']
        status = request.form['status']

        # Convert date string to date object
        date = datetime.strptime(date_str, '%Y-%m-%d').date()

        new_match = Match(title=title, date=date, status=status)
        db.session.add(new_match)
        db.session.commit()

        flash('New match added successfully!', 'success')
        return redirect(url_for('manage_matches'))

    return render_template('admin/add_match.html')

@app.route('/admin/delete_match/<int:match_id>', methods=['POST'])
@admin_required
def delete_match(match_id):
    match = Match.query.get(match_id)
    if match:
        db.session.delete(match)
        db.session.commit()
        flash('Match deleted successfully!', 'success')
    else:
        flash('Match not found.', 'danger')
    return redirect(url_for('manage_matches'))

@app.route('/admin/edit_match/<int:match_id>', methods=['GET', 'POST'])
@admin_required
def edit_match(match_id):
    match = Match.query.get(match_id)
    if not match:
        flash('Match not found.', 'danger')
        return redirect(url_for('manage_matches'))

    if request.method == 'POST':
        match.title = request.form['title']
        match.date = request.form['date']
        match.status = request.form['status']

        db.session.commit()
        flash('Match updated successfully!', 'success')
        return redirect(url_for('manage_matches'))

    return render_template('edit_match.html', match=match)


# Function to display match cards on the homepage
@app.route('/')
def display_matches():
    upcoming_matches = Match.query.filter_by(status='upcoming').all()
    ongoing_matches = Match.query.filter_by(status='ongoing').all()
    old_matches = Match.query.filter_by(status='old').all()
    return render_template('index.html', 
                           upcoming_matches=upcoming_matches, 
                           ongoing_matches=ongoing_matches, 
                           old_matches=old_matches)

@app.route('/view_matches/<match_type>')
def view_matches(match_type):
    if match_type == 'upcoming':
        matches = Match.query.filter_by(status='upcoming').all()
        title = "Upcoming Matches"
    elif match_type == 'ongoing':
        matches = Match.query.filter_by(status='ongoing').all()
        title = "Ongoing Matches"
    elif match_type == 'old':
        matches = Match.query.filter_by(status='old').all()
        title = "Old Matches"
    else:
        flash('Invalid match type.', 'danger')
        return redirect(url_for('index'))

    return render_template('view_matches.html', matches=matches, title=title)
# Faulty ---------
@app.route('/admin/manage_transactions', methods=['GET', 'POST'])
@admin_required
def manage_transactions():
    if request.method == 'POST':
        transaction_id = request.form.get('transaction_id')
        action = request.form.get('action')

        if not transaction_id:
            flash('Transaction ID is missing.', 'danger')
            return redirect(url_for('manage_transactions'))

        transaction = db.session.get(Transaction, transaction_id)  # Updated to use db.session.get()

        if not transaction:
            flash('Transaction not found.', 'danger')
            return redirect(url_for('manage_transactions'))

        if transaction.status != 'pending':
            flash('Transaction has already been processed.', 'danger')
            return redirect(url_for('manage_transactions'))

        try:
            if action == 'approve':
                transaction.status = 'approved'
                user = db.session.get(User, transaction.user_id)  # Updated to use db.session.get()

                if user:
                    if transaction.transaction_type == 'deposit':
                        user.wallet_balance += transaction.amount
                        print(f"Deposited {transaction.amount} to user {user.id}. New balance: {user.wallet_balance}")
                    elif transaction.transaction_type == 'withdrawal':
                        user.wallet_balance -= transaction.amount
                        print(f"Withdrew {transaction.amount} from user {user.id}. New balance: {user.wallet_balance}")

                        if user.upi_id:
                            amount1 = transaction.amount
                            upi_id = user.upi_id
                            redirect_url = f'upi://pay?pa={upi_id}&pn=YourName&mc=0000&tid=000000000000&tt=123&am={amount1}&cu=INR&url='
                            db.session.commit()
                            return redirect(redirect_url)
                    
                    db.session.commit()
                    flash('Transaction approved and wallet updated.', 'success')
                else:
                    flash('User associated with the transaction not found.', 'danger')

            elif action == 'reject':
                transaction.status = 'rejected'
                db.session.commit()
                flash('Transaction rejected.', 'info')

            else:
                flash('Invalid action.', 'danger')
                return redirect(url_for('manage_transactions'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error processing transaction: {str(e)}', 'danger')
            return redirect(url_for('manage_transactions'))

    pending_transactions = Transaction.query.filter_by(status='pending').all()
    return render_template('admin/manage_transactions.html', transactions=pending_transactions)



 
# Create database and tables if they don't exist
with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True)




