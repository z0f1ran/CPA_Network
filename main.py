from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import secrets
from sqlalchemy import create_engine
import hashlib

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:1234@127.0.0.1/cpa_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.String(10), primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    tracking_links = db.relationship('TrackingLink', backref='user', lazy=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# Маршрут для регистрации нового пользователя
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Проверка наличия пользователя с таким именем
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('register.html', error='Пользователь с таким именем уже существует')

        # Создание нового пользователя
        new_user = User(id=generate_tracking_id(), username=username, password=hashlib.sha256(password.encode('utf-8')).hexdigest())
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

# Маршрут для входа пользователя
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and hashlib.sha256(password.encode('utf-8')).hexdigest() == user.password:
            login_user(user)
            return redirect(url_for('index'))

        return render_template('login.html', error='Неверное имя пользователя или пароль')

    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user_links = TrackingLink.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', user_links=user_links)


# Маршрут для выхода пользователя
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

class TrackingLink(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    original_url = db.Column(db.String(500), nullable=False)
    click_count = db.Column(db.Integer, default=0)
    hash_token = db.Column(db.String(64), nullable=False, unique=True)
    user_id = db.Column(db.String(10), db.ForeignKey('user.id'), nullable=False)

def generate_tracking_id():
    return secrets.token_urlsafe(5)

def generate_hash_token():
    return hashlib.sha256(secrets.token_bytes(32)).hexdigest()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
@login_required
def generate_link():
    original_url = request.form.get('original_url')
    tracking_id = generate_tracking_id()
    hash_token = generate_hash_token()
    
    new_link = TrackingLink(id=tracking_id, original_url=original_url, hash_token=hash_token, user_id=current_user.id)
    db.session.add(new_link)
    db.session.commit()

    tracking_url = url_for('track_link', tracking_id=tracking_id, _external=True)
    stats_url = url_for('view_stats', hash_token=hash_token, _external=True)

    return render_template('generated_link.html', tracking_url=tracking_url, stats_url=stats_url, hash_token=hash_token)

@app.route('/<tracking_id>')
def track_link(tracking_id):
    link = TrackingLink.query.filter_by(id=tracking_id).first()
    if link:
        link.click_count += 1
        db.session.commit()
        return redirect(link.original_url)
    else:
        return render_template('404.html'), 404

@app.route('/stats', methods=['POST'])
def view_stats():
    hash_token = request.form.get('hash_token')
    link = TrackingLink.query.filter_by(hash_token=hash_token).first()
    if link:
        return render_template('stats.html', link=link)
    else:
        return render_template('404.html'), 404
    
if __name__ == '__main__':
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    db.create_all(app=app)
    app.run(debug=True)