import telegram
import os
import datetime
from flask import render_template
from app.telebot import telegram_bot
from app.models import Announcement, Company

def send_new_announcement(announcements):
    for announcement in announcements:
        response = announcement_message(announcement)
        if response:
            telegram_bot.sendMessage(chat_id='42704748', text=response, parse_mode='HTML')
            print("Announcement sent.")
    return "Job done."

def announcement_message(announcement):
    just_in = False
    if announcement.announced_date >= datetime.datetime.now() - datetime.timedelta(days=1):
        just_in = True
    announcement_input = {
            'just_in': just_in,
            'announced_company': announcement.announced_company.company_name,
            'announcement_title': announcement.title,
            'announced_date': str(announcement.announced_date.date().strftime('%d/%m/%Y')),
            'ann_id': announcement.ann_id
            }
    return render_template('message_template.html', announcement_input=announcement_input)
