@app.route('/admin/manage_transactions', methods=['GET', 'POST'])
@admin_required
def manage_transactions():
    if request.method == 'POST':
        # Get the transaction ID and action from the form
        transaction_id = request.form.get('transaction_id')
        action = request.form.get('action')

        # Validate transaction ID
        if transaction_id is None:
            flash('Transaction ID is missing.', 'danger')
            return redirect(url_for('manage_transactions'))

        # Find the transaction by ID
        transaction = Transaction.query.get(transaction_id)

        # Validate the transaction
        if transaction is None:
            flash('Transaction not found.', 'danger')
            return redirect(url_for('manage_transactions'))

        if transaction.status != 'pending':
            flash('Transaction has already been processed.', 'danger')
            return redirect(url_for('manage_transactions'))

        # Process the transaction based on the action
        if action == 'approve':
            transaction.status = 'approved'
            if current_user.wallet_balance is None:
                current_user.wallet_balance = 0.0
            transaction.user.wallet_balance += transaction.amount
            db.session.commit()
            flash('Transaction approved and wallet updated.', 'success')
        elif action == 'reject':
            transaction.status = 'rejected'
            db.session.commit()
            flash('Transaction rejected.', 'info')
        else:
            flash('Invalid action.', 'danger')
            return redirect(url_for('manage_transactions'))

    # Fetch all pending transactions
    pending_transactions = Transaction.query.filter_by(status='pending').all()
    return render_template('admin/manage_transactions.html', transactions=pending_transactions)