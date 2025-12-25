# models/plan.py
from models import db
from datetime import datetime

class Plan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    preferences = db.Column(db.Text) 
    contenu = db.Column(db.Text)       
    status = db.Column(db.String(20), default='en_cours')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
