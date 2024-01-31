from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import secrets
from sqlalchemy import create_engine
import hashlib

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:1234@127.0.0.1/cpa_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class TrackingLink(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    original_url = db.Column(db.String(500), nullable=False)
    click_count = db.Column(db.Integer, default=0)
    hash_token = db.Column(db.String(64), nullable=False, unique=True)

def generate_tracking_id():
    return secrets.token_urlsafe(5)

def generate_hash_token():
    return hashlib.sha256(secrets.token_bytes(32)).hexdigest()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_link():
    original_url = request.form.get('original_url')
    tracking_id = generate_tracking_id()
    hash_token = generate_hash_token()
    
    new_link = TrackingLink(id=tracking_id, original_url=original_url, hash_token=hash_token)
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
        return "Link not found", 404

@app.route('/stats', methods=['POST'])
def view_stats():
    hash_token = request.form.get('hash_token')
    link = TrackingLink.query.filter_by(hash_token=hash_token).first()
    if link:
        return render_template('stats.html', link=link)
    else:
        return "Link not found", 404
    
if __name__ == '__main__':
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    db.create_all(app=app)
    app.run(debug=True)