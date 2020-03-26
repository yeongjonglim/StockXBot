import os
from flask import url_for, request
import telegram
from app import telebot_token, telegram_bot, db
from app.models import Company
from app.telebot import bp
from app.telebot.helper import check_intent, send_telegram

@bp.before_app_first_request
def setupWebhook():
    url = os.environ.get('HOST_URL')+url_for('{}.receivedMessage'.format(bp.name))
    print(url)
    webhook = telegram_bot.setWebhook('{url}'.format(url=url))
    print('Webhook object: ' + str(webhook))

@bp.route('/receivedMessage{}'.format(telebot_token),  methods=['POST'])
def receivedMessage():
    # retrieve the message in JSON and then transform it to Telegram object
    update = telegram.Update.de_json(request.get_json(force=True), telegram_bot)
    print(update)

    if update.message:
        message = update.message
        chat = update.message.chat

        # Telegram understands UTF-8, so encode text for unicode compatibility
        text = update.message.text.encode('utf-8').decode()
        print("Got text message: ", text)

        chat.send_action('TYPING')

        response = check_intent(chat, text)
        reply_markup = telegram.InlineKeyboardMarkup(response["markup"]) if response["markup"] else None

        message.reply_text(text=response["response_text"], reply_markup=reply_markup, parse_mode='HTML')

    elif update.callback_query:
        callback_query = update.callback_query
        chat = callback_query.message.chat
        text = callback_query.data

        response = check_intent(chat, text, callback_query=True)
        callback_query.answer()
        reply_markup = telegram.InlineKeyboardMarkup(response["markup"]) if response["markup"] else None

        callback_query.edit_message_text(text=response["response_text"], reply_markup=reply_markup, parse_mode='HTML')

    else:
        print("Unknown type of request.")

    db.session.commit()

    return 'ok', 200
