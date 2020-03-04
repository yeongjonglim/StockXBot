from flask import current_app
from app import db
from datetime import datetime

subscribe = db.Table('subscribe',
    db.Column('telegram_id', db.Integer, db.ForeignKey('telegramsubscriber.id')),
    db.Column('company_id', db.Integer, db.ForeignKey('company.id'))
)

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_code = db.Column(db.String(8), index=True, unique=True, nullable=False)
    stock_name = db.Column(db.String(32), index=True, nullable=False)
    company_name = db.Column(db.String(128), index=True, nullable=False)
    company_site = db.Column(db.String(256))
    market = db.Column(db.String(32), nullable=False)
    sector = db.Column(db.String(64), nullable=False)
    announcement = db.relationship('Announcement', backref='announced_company', lazy='dynamic')
    subscriber = db.relationship('TelegramSubscriber', secondary=subscribe, backref='subscribed_company', lazy='dynamic')

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
    __tablename__ = "telegramsubscriber"
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, index=True, unique=True, nullable=False)
    joined_datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    subscribed_company = db.relationship('Company', secondary=subscribe, backref='subscriber', lazy='dynamic')

    def __repr__(self):
        return '<TelegramSubscriber {}>'.format(self.chat_id)

    def subscribes(self, company):
        if not self.has_subscribed(company):
            self.subscribed_company.append(company)

    def unsubscribes(self, company):
        if self.has_subscribed(company):
            self.subscribed_company.remove(company)

    def has_subscribed(self, company):
        return self.subscribed_company.filter(subscribe.c.company_id == company.id).count() > 0

    def subscribed_announcements(self):
        return Announcement.query.join(subscribe, (subscribe.c.company_id == Announcement.company_id)).filter(subscribe.c.telegram_id == self.id).order_by(Announcement.announced_date.desc())





