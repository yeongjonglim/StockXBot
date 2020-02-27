from flask import url_for, request
import telegram
from app.telebot import bp
from app.models import Announcement, Company
from app.helpers.telebot_jobs import send_announcement
from app import telebot_token, telegram_bot
import os

@bp.route('/setwebhook', methods=['GET', 'POST'])
def setupWebhook():
    webhook = telegram_bot.setWebhook('{url}'.format(url=os.environ.get('TELEBOT_URL')+url_for('.receivedMessage')+telebot_token))
    if webhook:
        return "webhook ok"
    else:
        return "webhook not ok"

@bp.route('/receivedMessage{}'.format(telebot_token),  methods=['POST'])
def receivedMessage():
    # retrieve the message in JSON and then transform it to Telegram object
    update = telegram.Update.de_json(request.get_json(force=True), telegram_bot)
    print(update)

    try:
        chat_id = update.message.chat.id
        msg_id = update.message.message_id
    except:
        print("chat_id and msg_id not found")
        chat_id = None
        msg_id = None

    if chat_id and msg_id:
        # Telegram understands UTF-8, so encode text for unicode compatibility
        text = update.message.text.encode('utf-8').decode()
        print("Got text message: ", text)

        queried_company = Company.query.filter_by(stock_name=text).first()
        queried_announcements = Announcement.query.filter_by(announced_company=queried_company).order_by(Announcement.id).limit(3).all()
        sent_status = send_announcement(queried_announcements, chat_id=chat_id)

    return 'ok', 200
