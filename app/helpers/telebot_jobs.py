import telegram
import os
from app.telebot import telegram_bot
from app.helpers import query_response
from app.models import Announcement, Company

def send_new_announcement(announcements):
    for announcement in announcements:
        response = query_response.announcement_message(announcement)
        if response:
            telegram_bot.sendMessage(chat_id='42704748', text=response, parse_mode='HTML')
            return "Announcement sent."
    return "Job done."
