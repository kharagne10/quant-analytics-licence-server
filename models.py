from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Licence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_email = db.Column(db.String(120), nullable=False)
    key = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending / paid / active
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
