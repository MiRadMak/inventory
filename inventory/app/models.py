from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
from app import db, login_manager
import json


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False, default='user')
    password_hash = db.Column(db.String(256), nullable=False)
    department = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Equipment(db.Model):
    __tablename__ = 'equipment'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    model = db.Column(db.String(100), index=True)
    type = db.Column(db.String(50), index=True)
    category = db.Column(db.String(50), index=True)
    location = db.Column(db.String(100), index=True)
    status = db.Column(db.String(50), index=True)
    inventory_number = db.Column(db.String(50), unique=True, index=True)
    serial_number = db.Column(db.String(100), index=True)
    ip_address = db.Column(db.String(45), index=True)
    mac_address = db.Column(db.String(17))
    description = db.Column(db.Text)

    specifications = db.Column(db.JSON)

    purchase_date = db.Column(db.Date)
    warranty_expiry = db.Column(db.Date)
    price = db.Column(db.Numeric(10, 2))
    supplier = db.Column(db.String(100))

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    creator = db.relationship('User', backref='equipment_created')

    def __repr__(self):
        return f'<Equipment {self.name}>'


class Maintenance(db.Model):
    __tablename__ = 'maintenance'
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False, index=True)
    technician_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    type = db.Column(db.String(50))
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='planned', index=True)
    scheduled_date = db.Column(db.DateTime, index=True)
    completed_date = db.Column(db.DateTime)
    cost = db.Column(db.Numeric(10, 2))
    parts_used = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    equipment = db.relationship('Equipment', backref='maintenance_records')
    technician = db.relationship('User', backref='maintenance_records')


class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False, index=True)
    assigned_to = db.Column(db.String(100))
    department = db.Column(db.String(100))
    assignment_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    return_date = db.Column(db.DateTime)
    purpose = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    equipment = db.relationship('Equipment', backref='assignments')


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)
    resource_id = db.Column(db.Integer, index=True)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref='audit_logs')

