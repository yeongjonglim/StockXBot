from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import telegram
import os

db = SQLAlchemy()
migrate = Migrate()

telebot_token = os.environ.get('TELEBOT_TOKEN')
telegram_bot = telegram.Bot(telebot_token)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.telebot import bp as telebot_bp
    app.register_blueprint(telebot_bp)

    return app

from app import models
