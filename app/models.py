from flask import current_app
from app import db
from datetime import datetime

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_code = db.Column(db.String(8), index=True, unique=True, nullable=False)
    stock_name = db.Column(db.String(32), index=True, nullable=False)
    company_name = db.Column(db.String(128), index=True, nullable=False)
    company_site = db.Column(db.String(256))
    market = db.Column(db.String(32), nullable=False)
    sector = db.Column(db.String(32), nullable=False)
    announcements = db.relationship('Announcement', backref='announced_company', lazy='dynamic')

    def __repr__(self):
        return '<Company {}>'.format(self.stock_name)

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(128))
    announced_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ann_id = db.Column(db.String(16), unique=True, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    title = db.Column(db.String(1024))

    def __repr__(self):
        return '<Announcement {}>'.format(self.title)

class TelegramSubscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, index=True, unique=True, nullable=False)

    def __repr__(self):
        return '<TelegramSubsriber {}>'.format(self.chat_id)
