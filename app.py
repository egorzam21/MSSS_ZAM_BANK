from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime
import random
import string
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sberbank-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sberbank.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# ─── MODELS ───────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    accounts = db.relationship('Account', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    account_number = db.Column(db.String(20), unique=True, nullable=False)
    account_type = db.Column(db.String(50), nullable=False)  # checking, savings, credit
    currency = db.Column(db.String(3), default='RUB')
    balance = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sent_transactions = db.relationship('Transaction', foreign_keys='Transaction.from_account_id', backref='sender', lazy=True)
    received_transactions = db.relationship('Transaction', foreign_keys='Transaction.to_account_id', backref='receiver', lazy=True)

    def get_all_transactions(self):
        all_tx = self.sent_transactions + self.received_transactions
        return sorted(all_tx, key=lambda x: x.created_at, reverse=True)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=True)
    to_account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), default='Перевод')
    transaction_type = db.Column(db.String(50), nullable=False)  # transfer, deposit, withdrawal
    status = db.Column(db.String(20), default='completed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reference = db.Column(db.String(20))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def generate_account_number():
    while True:
        num = '4081' + ''.join(random.choices(string.digits, k=16))
        if not Account.query.filter_by(account_number=num).first():
            return num

def generate_reference():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

ACCOUNT_TYPES = {
    'checking': {'name': 'Текущий счёт', 'icon': 'wallet', 'bonus': 10000.0},
    'savings': {'name': 'Сберегательный', 'icon': 'piggy-bank', 'bonus': 50000.0},
    'credit': {'name': 'Кредитный', 'icon': 'credit-card', 'bonus': 100000.0},
}


# ─── AUTH ROUTES ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not all([full_name, phone, email, password]):
            flash('Заполните все поля', 'error')
            return render_template('register.html')
        if password != confirm:
            flash('Пароли не совпадают', 'error')
            return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('Email уже зарегистрирован', 'error')
            return render_template('register.html')
        if User.query.filter_by(phone=phone).first():
            flash('Телефон уже зарегистрирован', 'error')
            return render_template('register.html')

        user = User(full_name=full_name, phone=phone, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        # Create default checking account with welcome bonus
        acc = Account(
            user_id=user.id,
            account_number=generate_account_number(),
            account_type='checking',
            balance=10000.0
        )
        db.session.add(acc)
        db.session.flush()

        tx = Transaction(
            from_account_id=None,
            to_account_id=acc.id,
            amount=10000.0,
            description='Приветственный бонус',
            transaction_type='deposit',
            reference=generate_reference()
        )
        db.session.add(tx)
        db.session.commit()

        login_user(user)
        flash('Добро пожаловать в СберБанк!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        login_val = request.form.get('login', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter(
            (User.email == login_val) | (User.phone == login_val)
        ).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect(url_for('dashboard'))
        else:
            flash('Неверный логин или пароль', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# ─── MAIN ROUTES ──────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    accounts = Account.query.filter_by(user_id=current_user.id, is_active=True).all()
    total = sum(a.balance for a in accounts)

    # Recent transactions across all accounts
    all_tx = []
    for acc in accounts:
        all_tx.extend(acc.get_all_transactions())
    all_tx = sorted(all_tx, key=lambda x: x.created_at, reverse=True)[:10]

    return render_template('dashboard.html', accounts=accounts, total=total, transactions=all_tx, now=datetime.utcnow())


@app.route('/accounts')
@login_required
def accounts():
    accs = Account.query.filter_by(user_id=current_user.id, is_active=True).all()
    return render_template('accounts.html', accounts=accs, account_types=ACCOUNT_TYPES)


@app.route('/accounts/open', methods=['POST'])
@login_required
def open_account():
    acc_type = request.form.get('account_type')
    if acc_type not in ACCOUNT_TYPES:
        flash('Неверный тип счёта', 'error')
        return redirect(url_for('accounts'))

    existing = Account.query.filter_by(user_id=current_user.id, account_type=acc_type, is_active=True).count()
    if existing >= 3:
        flash('Максимальное количество счетов данного типа достигнуто', 'error')
        return redirect(url_for('accounts'))

    bonus = ACCOUNT_TYPES[acc_type]['bonus']
    acc = Account(
        user_id=current_user.id,
        account_number=generate_account_number(),
        account_type=acc_type,
        balance=bonus
    )
    db.session.add(acc)
    db.session.flush()

    tx = Transaction(
        from_account_id=None,
        to_account_id=acc.id,
        amount=bonus,
        description=f'Открытие счёта — {ACCOUNT_TYPES[acc_type]["name"]}',
        transaction_type='deposit',
        reference=generate_reference()
    )
    db.session.add(tx)
    db.session.commit()
    flash(f'Счёт открыт! Начислен бонус {bonus:,.0f} ₽', 'success')
    return redirect(url_for('accounts'))


@app.route('/accounts/<int:account_id>/close', methods=['POST'])
@login_required
def close_account(account_id):
    acc = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    user_accounts = Account.query.filter_by(user_id=current_user.id, is_active=True).count()
    if user_accounts <= 1:
        flash('Нельзя закрыть последний счёт', 'error')
        return redirect(url_for('accounts'))
    acc.is_active = False
    db.session.commit()
    flash('Счёт закрыт', 'success')
    return redirect(url_for('accounts'))


@app.route('/transfer', methods=['GET', 'POST'])
@login_required
def transfer():
    accounts = Account.query.filter_by(user_id=current_user.id, is_active=True).all()
    if request.method == 'POST':
        from_id = request.form.get('from_account')
        to_number = request.form.get('to_account_number', '').strip()
        amount = request.form.get('amount', 0)
        description = request.form.get('description', 'Перевод').strip() or 'Перевод'

        try:
            amount = float(amount)
        except (ValueError, TypeError):
            flash('Неверная сумма', 'error')
            return render_template('transfer.html', accounts=accounts)

        if amount <= 0:
            flash('Сумма должна быть больше нуля', 'error')
            return render_template('transfer.html', accounts=accounts)

        from_acc = Account.query.filter_by(id=from_id, user_id=current_user.id, is_active=True).first()
        if not from_acc:
            flash('Счёт списания не найден', 'error')
            return render_template('transfer.html', accounts=accounts)

        to_acc = Account.query.filter_by(account_number=to_number, is_active=True).first()
        if not to_acc:
            flash('Счёт получателя не найден', 'error')
            return render_template('transfer.html', accounts=accounts)

        if from_acc.id == to_acc.id:
            flash('Нельзя переводить на тот же счёт', 'error')
            return render_template('transfer.html', accounts=accounts)

        if from_acc.balance < amount:
            flash('Недостаточно средств', 'error')
            return render_template('transfer.html', accounts=accounts)

        from_acc.balance -= amount
        to_acc.balance += amount

        tx = Transaction(
            from_account_id=from_acc.id,
            to_account_id=to_acc.id,
            amount=amount,
            description=description,
            transaction_type='transfer',
            reference=generate_reference()
        )
        db.session.add(tx)
        db.session.commit()

        flash(f'Перевод {amount:,.2f} ₽ выполнен успешно!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('transfer.html', accounts=accounts)


@app.route('/history')
@login_required
def history():
    accounts = Account.query.filter_by(user_id=current_user.id, is_active=True).all()
    account_id = request.args.get('account_id', type=int)

    if account_id:
        acc = Account.query.filter_by(id=account_id, user_id=current_user.id).first()
        transactions = acc.get_all_transactions() if acc else []
        selected = account_id
    else:
        all_tx = []
        for acc in accounts:
            all_tx.extend(acc.get_all_transactions())
        transactions = sorted(all_tx, key=lambda x: x.created_at, reverse=True)
        selected = None

    return render_template('history.html', transactions=transactions, accounts=accounts, selected=selected)


@app.route('/profile')
@login_required
def profile():
    accounts = Account.query.filter_by(user_id=current_user.id, is_active=True).all()
    total = sum(a.balance for a in accounts)
    return render_template('profile.html', total=total)


# ─── API ──────────────────────────────────────────────────────────────────────

@app.route('/api/check-account', methods=['POST'])
@login_required
def check_account():
    number = request.json.get('number', '').strip()
    acc = Account.query.filter_by(account_number=number, is_active=True).first()
    if acc:
        return jsonify({'found': True, 'owner': acc.owner.full_name, 'type': ACCOUNT_TYPES.get(acc.account_type, {}).get('name', '')})
    return jsonify({'found': False})


@app.route('/api/stats')
@login_required
def api_stats():
    accounts = Account.query.filter_by(user_id=current_user.id, is_active=True).all()
    account_ids = [a.id for a in accounts]
    
    income = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.to_account_id.in_(account_ids),
        Transaction.transaction_type == 'transfer'
    ).scalar() or 0

    expense = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.from_account_id.in_(account_ids),
        Transaction.transaction_type == 'transfer'
    ).scalar() or 0

    return jsonify({'income': income, 'expense': expense, 'balance': sum(a.balance for a in accounts)})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
