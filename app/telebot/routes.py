from flask import url_for, request
import telegram
from app import telebot_token, telegram_bot, db
from app.telebot import bp
from app.telebot.helper import check_intent, send_telegram
import os

@bp.route('/setwebhook', methods=['GET', 'POST'])
def setupWebhook():
    print(os.environ.get('HOST_URL')+'/telebot/receivedMessage'+telebot_token)
    webhook = telegram_bot.setWebhook('{url}'.format(url=os.environ.get('HOST_URL')+'/telebot/receivedMessage'+telebot_token))
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

        # Telegram understands UTF-8, so encode text for unicode compatibility
        text = update.message.text.encode('utf-8').decode()
        print("Got text message: ", text)

        check_intent(chat_id, text)
        db.session.commit()

    except:
        print("Error in receivedMessage")

    return 'ok', 200
