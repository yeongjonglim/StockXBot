from flask import Blueprint, current_app

bp = Blueprint('telebot', __name__, url_prefix='/telebot')

from app.telebot import routes
