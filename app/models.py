from datetime import datetime
from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    password = db.Column(db.String(255), default="DefaultPass123!")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'enabled': self.enabled,
            'password': self.password,
            'created_at': self.created_at.isoformat()
        }

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text)
    
    members = db.relationship('User', secondary='group_members', backref='groups')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'members': [m.email for m in self.members]
        }

group_members = db.Table(
    'group_members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'))
)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'action': self.action,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }