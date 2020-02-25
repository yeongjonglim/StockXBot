from flask import url_for, request
import telegram
from app.telebot import bp, telegram_bot
from app.helpers import query_response
from app.models import Announcement, Company
import os

telebot_token = os.environ.get('TELEBOT_TOKEN')

@bp.route('/setwebhook', methods=['GET', 'POST'])
def setupWebhook():
    webhook = telegram_bot.setWebhook('{url}'.format(url=os.environ.get('TELEBOT_URL')+url_for('.receivedMessage')+telebot_token))
    if webhook:
        return "webhook ok"
    else:
        return "webhook not ok"

@bp.route('/receivedMessage'+telebot_token,  methods=['POST'])
def receivedMessage():
    # retrieve the message in JSON and then transform it to Telegram object
    update = telegram.Update.de_json(request.get_json(force=True), telegram_bot)

    chat_id = update.message.chat.id
    msg_id = update.message.message_id

    # Telegram understands UTF-8, so encode text for unicode compatibility
    text = update.message.text.encode('utf-8').decode()
    print("Got text message: ", text)

    queried_company = Company.query.filter_by(stock_name=text).first()
    response = query_response.announcement_message(Announcement.query.filter_by(announced_company=queried_company).all())
    telegram_bot.sendMessage(chat_id=chat_id, text=response, parse_mode='HTML')

    return 'ok', 200
