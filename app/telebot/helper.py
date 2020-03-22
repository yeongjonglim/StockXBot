import telegram
import os
import dialogflow_v2 as dialogflow
from app import telegram_bot, db
from app.models import Company, TelegramSubscriber, Announcement
from flask import current_app

def send_telegram(objects=None, chat_id=None, collate=False, message_function=None, **kwargs):
    """
    This function will take in list of objects to iterate them, generate the message using message_function according to collating flag.
    If no message_function is provided, the function will send the message from objects argument, the object will not be manipulated in any way.
    Collating is to allow the message to be sent either in a single message or multiple messages when given a list of objects.
    """
    if not message_function:
        telegram_bot.sendMessage(chat_id=chat_id[0], text=objects, parse_mode='HTML')
    else:
        if collate:
            print("Generating response template...")
            response = message_function(objects, **kwargs)
            print("Reponse template generated.")
            if not len(response) == 0:
                for chat in chat_id:
                    telegram_bot.sendMessage(chat_id=chat, text=response, parse_mode='HTML')
        else:
            print("non collating selected")
            for obj in objects:
                response = message_function(obj, **kwargs)
                if response:
                    for chat in chat_id:
                        print("Sending to ..." + str(chat))
                        telegram_bot.sendMessage(chat_id=chat, text=response, parse_mode='HTML')

def check_intent(chat_id, text):
    """
    This will help determine types of intents by users
    1. getSubscribedCompany: This will return list of companies that the user has subscribed to (must be existing user)
    2. getAnnouncement <Company>: This will return list of announcements published by the <Company> that the user has queried to (must have company)
    3. subscribeCompany <Company>: This will add the <Company> into the user list company of subscription (must have company)
    4. unsubscribeCompany <Company>: This will remove the <Company> from the user list company of subscription (must be existing user and have company)
    5. generic intents to handle fallback and default intent
    """
    print('Getting response from DialogFlow')
    response = detect_intent_text(os.environ.get('PROJECT_ID'), chat_id, text, 'en')
    intent = response.query_result.intent.display_name
    companies = response.query_result.parameters.fields.get('company').list_value.values if response.query_result.parameters.fields.get('company') else None
    print(companies)
    fulfillment_text = response.query_result.fulfillment_text

    company_ind = 0
    message = None
    while True:
        company = companies[company_ind].string_value if companies else None
        comp = Company.query.filter_by(stock_code=company).first()
        user = TelegramSubscriber.query.filter_by(chat_id=chat_id).first()

        # Checking the combination between comp, company(user input), user(user from database) and intent to guess what is the user trying to do.
        if intent == "defaultFallbackIntent" or intent == "defaultWelcomeIntent" or intent == "getAgentInformation" or (intent == 'unsubscribeCompany' and not company) or (intent == 'getAnnouncement' and not company) or (intent == 'subscribeCompany' and not company):
            send_telegram(objects=fulfillment_text, chat_id=[chat_id])
        elif current_app.elasticsearch and (not comp and company):
            query, total = Company.search(company, 1, 10)
            detect_intent_text(os.environ.get('PROJECT_ID'), chat_id, intent, 'en')
            send_telegram(objects=query.all(), chat_id=[chat_id], collate=True, message_function=Company.company_message, message="More than one stock is matching to your query, please specify your selection further:")
        elif user and comp and intent == "unsubscribeCompany":
            if user.subs_company.filter_by(stock_code=company).first():
                user.unsubscribes(comp)
                send_telegram(objects="Thank you! You are now unsubscribed from " + comp.company_name, chat_id=[chat_id])
            else:
                send_telegram(objects="Sorry, you are not subscribed to " + comp.company_name, chat_id=[chat_id])
        elif comp:
            if intent == 'getAnnouncement':
                send_telegram(objects=comp.announcement.limit(5).all(), chat_id=[chat_id], message_function=Announcement.announcement_message)
            elif intent == 'subscribeCompany':
                if user:
                    if not user.subs_company.filter_by(stock_code=company).first():
                        user.subscribes(comp)
                        send_telegram(objects="Thank you! You are now subscribed to " + comp.company_name, chat_id=[chat_id])
                    else:
                        send_telegram(objects="Sorry, you are already subscribed to " + comp.company_name, chat_id=[chat_id])
                else:
                    user = TelegramSubscriber(chat_id=chat_id)
                    db.session.add(user)
                    user.subscribes(comp)
                    send_telegram(objects="Welcome onboard! Thank you for your first subscription on " + comp.company_name, chat_id=[chat_id])
        elif user and not comp and intent == 'getSubscribedCompany':
            send_telegram(objects=user.subscribed_company, chat_id=[chat_id], collate=True, message_function=Company.company_message, message="Thank you for subscribing, this is your subscription list:")
        else:
            send_telegram(objects="Sorry, we are unable to understand you, try asking me what can I do.", chat_id=[chat_id])

        # Checking if it is last item, if last then break else go next
        if not companies or company_ind == len(companies)-1:
            break
        else:
            company_ind += 1

def detect_intent_text(project_id, session_id, text, language_code):
    """Returns the result of detect intent with texts as inputs.
    Using the same `session_id` between requests allows continuation of the conversation."""
    session_client = dialogflow.SessionsClient()

    session = session_client.session_path(project_id, session_id)
    print('Session path: {}\n'.format(session))

    # for text in texts:
    text_input = dialogflow.types.TextInput(text=text, language_code=language_code)

    query_input = dialogflow.types.QueryInput(text=text_input)

    response = session_client.detect_intent(session=session, query_input=query_input)

    print('=' * 20)
    print('Query text: {}'.format(response.query_result.query_text))
    print('Detected intent: {} (confidence: {})\n'.format(response.query_result.intent.display_name,response.query_result.intent_detection_confidence))
    print('Fulfillment text: {}\n'.format(response.query_result.fulfillment_text))

    return response
