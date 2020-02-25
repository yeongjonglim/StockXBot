from flask import Blueprint, current_app
import telegram
import os

bp = Blueprint('telebot', __name__, url_prefix='/telebot')

telegram_bot = telegram.Bot(token=os.environ.get('TELEBOT_TOKEN'))

from app.telebot import routes
