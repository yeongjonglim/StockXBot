import os
from flask import url_for, request
import telegram
from app import telebot_token, telegram_bot, db
from app.models import Company
from app.telebot import bp
from app.telebot.helper import check_intent, send_telegram

@bp.route('/setwebhook', methods=['GET', 'POST'])
def setupWebhook():
    url = os.environ.get('HOST_URL')+url_for('.receivedMessage')
    print(url)
    webhook = telegram_bot.setWebhook('{url}'.format(url=url))
    Company.reindex()
    if webhook:
        return "webhook ok"
    else:
        return "webhook not ok"

@bp.route('/receivedMessage{}'.format(telebot_token),  methods=['POST'])
def receivedMessage():
    # retrieve the message in JSON and then transform it to Telegram object
    update = telegram.Update.de_json(request.get_json(force=True), telegram_bot)
    print(update)

    chat_id = update.message.chat.id
    msg_id = update.message.message_id

    # Telegram understands UTF-8, so encode text for unicode compatibility
    text = update.message.text.encode('utf-8').decode()
    print("Got text message: ", text)

    if text:
        check_intent(chat_id, text)
        db.session.commit()
    else:
        print("No text provided.")

    return 'ok', 200
