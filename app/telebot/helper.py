import os
import telegram
import dialogflow_v2 as dialogflow
from flask import current_app, render_template
from app import telegram_bot, db
from app.models import Company, TelegramSubscriber, Announcement
from app.email import send_email

def pagination_button(total, page, per_page, target_intent, company=None):
    has_next = (total - (page*per_page)) > 0
    has_prev = page > 1
    buttons = []

    if has_prev:
        # if has prev page, create a button for previous page
        prev_button = telegram.InlineKeyboardButton(text="◀ Previous Page", callback_data="{}@{}@{}".format(target_intent, company, page-1))
        buttons.append(prev_button)

    if has_next:
        # if has next page, create a button for next page
        next_button = telegram.InlineKeyboardButton(text="Next Page ▶", callback_data="{}@{}@{}".format(target_intent, company, page+1))
        buttons.append(next_button)

    return buttons

def check_intent(chat, text, callback_query=False):
    """
    This will help determine types of intents by users
    1. getSubscribedCompany: This will return list of companies that the user has subscribed to (must be existing user)
    2. getAnnouncement <Company>: This will return list of announcements published by the <Company> that the user has queried to (must have company)
    3. subscribeCompany <Company>: This will add the <Company> into the user list company of subscription (must have company)
    4. unsubscribeCompany <Company>: This will remove the <Company> from the user list company of subscription (must be existing user and have company)
    5. generic intents to handle fallback and default intent
    """
    chat_id = chat.id
    user = TelegramSubscriber.query.filter(TelegramSubscriber.chat_id==chat_id, TelegramSubscriber.status!=0).first()
    message = None
    markup = None
    response_text = None
    per_page = 4

    if callback_query:
        # Do if it is callback query
        intention = text.split('@')
        intent = intention[0]
        page = 1 if len(intention) <= 2 else int(intention[2])
        companies = [None if len(intention) <= 1 else intention[1]]
        price = None
    else:
        # Do if it is not callback query (generic text query)
        print('Getting response from DialogFlow')
        response = detect_intent_text(os.environ.get('PROJECT_ID'), chat_id, text, 'en')
        intent = response.query_result.intent.display_name
        companies = response.query_result.parameters.fields.get('company').list_value.values if response.query_result.parameters.fields.get('company') else None
        price = response.query_result.parameters.fields.get('price').number_value if response.query_result.parameters.fields.get('price') else None
        if companies:
            strings = []
            for company in companies:
                string = company.string_value
                strings.append(string)
            companies = strings
        fulfillment_text = response.query_result.fulfillment_text
        page = 1

        if user:
            if user.status == 2:
                intent = 'optOutFeedback'

    company_ind = 0
    while True:
        company = companies[company_ind] if companies else None
        comp = Company.query.filter_by(stock_code=company).first()

        # Checking the combination between comp, company(user input), user(user from database) and intent to guess what is the user trying to do.
        if intent == "defaultFallbackIntent":
            response_text = "I'm sorry, can you repeat that again or try one of the below options?"
            markup = [[
                telegram.InlineKeyboardButton(text="▶️ Start", callback_data="defaultWelcomeIntent"),
                telegram.InlineKeyboardButton(text="ℹ️ Help", callback_data="getAgentInformation")
                ]]

        elif intent == "defaultWelcomeIntent":
            response_text = "Hi {}, I will be your handler to fetch stock announcements from Bursa Malaysia. Feel free to explore my capabilities with /help.".format(chat.first_name)

        elif intent == "getAgentInformation":
            response_text = render_template('telebot/agent_info_template.html', user_name=chat.first_name)
            markup = [
                telegram.InlineKeyboardButton(text="Subscribe", callback_data="subscribeCompany")
                ]
            if user:
                user.update_name(chat)
                markup.append(telegram.InlineKeyboardButton(text="Unsubscribe", callback_data="unsubscribeCompany"))
                markup = [markup]
                markup.append([
                    telegram.InlineKeyboardButton(text="Check Subscription", callback_data="getSubscribedCompany"),
                    telegram.InlineKeyboardButton(text="Set Price Alert", callback_data="setPriceAlert")
                    ])
                markup.append([telegram.InlineKeyboardButton(text="⏹️ Opt Out", callback_data="optOut")])
            else:
                markup = [markup]

        elif intent == "subscribeCompany":
            if not company:
                # no company is typed
                detect_intent_text(os.environ.get('PROJECT_ID'), chat_id, intent, 'en')
                response_text = 'Please input the stock name that you are interested in.'
            elif not comp and current_app.elasticsearch:
                # no specific company is found in db
                response_text = 'This is the list of stocks that are nearest to your input.'
                query, total = Company.search(company, page, per_page)
                target_companies = query.all()
                buttons = []
                for target_company in target_companies:
                    button = telegram.InlineKeyboardButton(text="{stock_name}: {company_name} ({stock_code})".format(stock_name=target_company.stock_name, company_name=target_company.company_name, stock_code=target_company.stock_code), callback_data="subscribeCompany@{}".format(target_company.stock_code))
                    buttons.append(button)
                buttons = [buttons]
                markup = list(map(list, zip(*buttons)))
                # create pagination experience here
                page_buttons = pagination_button(total, page, per_page, intent, company=company)
                markup.append(page_buttons)
                markup.append([telegram.InlineKeyboardButton(text="ℹ️ Back to Help", callback_data="getAgentInformation")])
            elif not comp:
                # company input cannot be recognised without elasticsearch assistance
                detect_intent_text(os.environ.get('PROJECT_ID'), chat_id, intent, 'en')
                response_text = "Sorry, I can't find the company you are interested in, can you please specify the company with full name?"
            elif not user:
                # if new user
                if TelegramSubscriber.query.filter_by(chat_id=chat_id).first():
                    user = TelegramSubscriber.query.filter_by(chat_id=chat_id).first()
                    user.activate()
                else:
                    user = TelegramSubscriber(chat_id=chat_id, username=chat.username, first_name=chat.first_name, last_name=chat.last_name)
                    db.session.add(user)
                user.subscribes(comp)
                response_text = "Welcome {}! Thank you for your first subscription on {}".format(chat.first_name, comp.company_name)
                markup = [[
                    telegram.InlineKeyboardButton(text="Subscribe", callback_data="subscribeCompany")
                    ],
                    [telegram.InlineKeyboardButton(text="Check Subscription", callback_data="getSubscribedCompany"),
                    telegram.InlineKeyboardButton(text="Set Price Alert", callback_data="setPriceAlert")],
                    [telegram.InlineKeyboardButton(text="ℹ️ Back to Help", callback_data="getAgentInformation")]
                    ]
            elif user.has_subscribed(comp):
                # user already subscribed to the company
                response_text = "Sorry, you are already subscribed to {}.".format(comp.stock_name)
            else:
                # all conditions checked, user can now subscribe to the company
                user.subscribes(comp)
                response_text = "Thank you! You are now subscribed to {}.".format(comp.stock_name)
                markup = [[
                    telegram.InlineKeyboardButton(text="Subscribe", callback_data="subscribeCompany"),
                    telegram.InlineKeyboardButton(text="Undo", callback_data="unsubscribeCompany@{}".format(comp.stock_code))
                    ],
                    [telegram.InlineKeyboardButton(text="Check Subscription", callback_data="getSubscribedCompany"),
                    telegram.InlineKeyboardButton(text="Set Price Alert", callback_data="setPriceAlert")],
                    [telegram.InlineKeyboardButton(text="ℹ️ Back to Help", callback_data="getAgentInformation")]
                    ]

        elif intent == "unsubscribeCompany":
            if not user:
                # user has not subscribed before
                response_text = 'Hi {}, seems like it is your first time here, try /start or /help.'.format(chat.first_name)
                markup = [[
                    telegram.InlineKeyboardButton(text="Subscribe", callback_data="subscribeCompany")
                    ],
                    [telegram.InlineKeyboardButton(text="ℹ️ Back to Help", callback_data="getAgentInformation")]
                    ]
            elif not company or not comp:
                # no company is typed
                # can consider putting in the list of subscribed company as markup in pagination
                response_text = "Please select the stocks that you would like to unsubscribe."
                subscribed_companies = Company.query.filter(Company.subscriber.any(id=user.id)).order_by(Company.stock_name).paginate(page, per_page, False)
                # subscribed_companies = user.subscribed_company.order_by(Company.stock_name).paginate(page, per_page, False)
                buttons = []
                for subscribed_company in subscribed_companies.items:
                    button = telegram.InlineKeyboardButton(text="{stock_name}: {company_name} ({stock_code})".format(stock_name=subscribed_company.stock_name, company_name=subscribed_company.company_name, stock_code=subscribed_company.stock_code), callback_data="unsubscribeCompany@{}".format(subscribed_company.stock_code))
                    buttons.append(button)
                buttons = [buttons]
                markup = list(map(list, zip(*buttons)))
                # create pagination experience here
                page_buttons = pagination_button(subscribed_companies.total, page, per_page, intent, company=company)
                markup.append(page_buttons)
                markup.append([telegram.InlineKeyboardButton(text="ℹ️ Back to Help", callback_data="getAgentInformation")])
            elif user.has_subscribed(comp):
                # user has subscribed to the company, will proceed to unsubscribe
                user.unsubscribes(comp)
                response_text = "Thank you! You are now unsubscribed from {}.".format(comp.stock_name)
                markup = [[
                    telegram.InlineKeyboardButton(text="Unsubscribe", callback_data="unsubscribeCompany"),
                    telegram.InlineKeyboardButton(text="Undo", callback_data="subscribeCompany@{}".format(comp.stock_code))
                    ],
                    [telegram.InlineKeyboardButton(text="Check Subscription", callback_data="getSubscribedCompany"),
                    telegram.InlineKeyboardButton(text="ℹ️ Back to Help", callback_data="getAgentInformation")]
                    ]
            else:
                # user has not subcribed to the specific company
                response_text = 'You have not subscribed to {}.'.format(comp.stock_name)
                markup = [[
                    telegram.InlineKeyboardButton(text="Subscribe", callback_data="subscribeCompany"),
                    telegram.InlineKeyboardButton(text="Unsubscribe", callback_data="unsubscribeCompany")
                    ],
                    [telegram.InlineKeyboardButton(text="Check Subscription", callback_data="getSubscribedCompany"),
                    telegram.InlineKeyboardButton(text="ℹ️ Back to Help", callback_data="getAgentInformation")]
                    ]

        elif intent == "setPriceAlert":
            if not user:
                # user has not subscribed before
                response_text = 'Hi {}, seems like it is your first time here, try /start or /help.'.format(chat.first_name)
                markup = [[
                    telegram.InlineKeyboardButton(text="Subscribe", callback_data="subscribeCompany")
                    ]]
            elif not company or not comp:
                # no company is typed
                # can consider putting in the list of subscribed company as markup in pagination
                response_text = "Please select the stock that you would like to set price alert for."
                subscribed_companies = Company.query.filter(Company.subscriber.any(id=user.id)).order_by(Company.stock_name).paginate(page, per_page, False)
                buttons = []
                for subscribed_company in subscribed_companies.items:
                    button = telegram.InlineKeyboardButton(text="{stock_name}: {company_name} ({stock_code})".format(stock_name=subscribed_company.stock_name, company_name=subscribed_company.company_name, stock_code=subscribed_company.stock_code), callback_data="setPriceAlert@{}".format(subscribed_company.stock_code))
                    buttons.append(button)
                buttons = [buttons]
                markup = list(map(list, zip(*buttons)))
                # create pagination experience here
                page_buttons = pagination_button(subscribed_companies.total, page, per_page, intent, company=company)
                markup.append(page_buttons)
                markup.append([telegram.InlineKeyboardButton(text="ℹ️ Back to Help", callback_data="getAgentInformation")])
            elif not price and price != 0.0:
                # prompt users to input desired price
                response_text = "Please type the desired price."
                print(company)
                detect_intent_text(os.environ.get('PROJECT_ID'), chat_id, intent + " " + str(company), 'en')
            else:
                # all conditions checked, user exists, company exists with desired price
                user.set_price_alert(comp, price)
                response_text = "Your price alert has been subscribed successfully. You will be notified once the price is fulfilled."

        elif intent == "getSubscribedCompany":
            if not user:
                # user has not subscribed before
                response_text = 'Hi {}, seems like it is your first time here, try /start or /help.'.format(chat.first_name)
                markup = [[
                    telegram.InlineKeyboardButton(text="Subscribe", callback_data="subscribeCompany")
                    ],
                    [telegram.InlineKeyboardButton(text="ℹ️ Back to Help", callback_data="getAgentInformation")]
                    ]
            elif len(user.subscribed_company) == 0:
                # user has not subscribed to any companies
                response_text = "Hi {}, seems like it's been a while since you left us, try /start or /help to get started again!".format(chat.first_name)
                markup = [[
                    telegram.InlineKeyboardButton(text="Subscribe", callback_data="subscribeCompany")
                    ],
                    [telegram.InlineKeyboardButton(text="ℹ️ Back to Help", callback_data="getAgentInformation")]
                    ]
            else:
                # retrieve all companies that the user has subscribed to
                response_text = Company.company_message(user.subscribed_company, message="Thank you for subscribing, this is your subscription list:")
                markup = [[
                    telegram.InlineKeyboardButton(text="Subscribe", callback_data="subscribeCompany"),
                    telegram.InlineKeyboardButton(text="Unsubscribe", callback_data="unsubscribeCompany")
                    ],
                    [
                    telegram.InlineKeyboardButton(text="Set Price Alert", callback_data="setPriceAlert"),
                    telegram.InlineKeyboardButton(text="ℹ️ Back to Help", callback_data="getAgentInformation")
                    ]
                    ]


        elif 'optOut' in intent:
            if not user:
                # user have not subscribed before
                response_text = 'Sorry, you are not subscribed to us.'
            elif intent == 'optOutConfirmed':
                user.optout()
                response_text = "Sorry to see you go, please drop us a feedback here and we will improve our bot. Thank you."
            elif intent == 'optOutFeedback':
                user.deactivate()
                # constructing user's name in string
                if user.first_name and user.last_name:
                    user_name = user.first_name + " " + user.last_name
                elif user.first_name:
                    user_name = user.first_name
                elif user.last_name:
                    user_name = user.last_name
                else:
                    user_name = None
                send_email('Feedback from Telegram User',
                           sender='no-reply@'+current_app.config['MAIL_SERVER'],
                           recipients=current_app.config['ADMINS'],
                           text_body=render_template('email/feedback.txt', user=user_name, feedback_text=text),
                           html_body=render_template('email/feedback.html', user=user_name, feedback_text=text)
                           )
                response_text = "Thank you for your feedback. Our team has received your feedback and we hope to see you again."
            else:
                response_text = "Are you sure to opt out? Selecting 'Yes' is irreversible and will delete all your subscription record."
                markup = [[
                    telegram.InlineKeyboardButton(text="⭕ Yes", callback_data="optOutConfirmed"),
                    telegram.InlineKeyboardButton(text="❎ No", callback_data="getAgentInformation")
                    ]]

        else:
            # intent not recognised, call default fallback
            return check_intent(chat, "defaultFallbackIntent", callback_query=True)

        if not markup and intent != 'optOutConfirmed':
            markup = [[telegram.InlineKeyboardButton(text="ℹ️ Help", callback_data="getAgentInformation")]]

        # Checking if it is last item, if last then break else go next
        if not companies or company_ind == len(companies)-1:
            break
        else:
            company_ind += 1

    resp = {
            'response_text': response_text,
            'markup': markup
            }
    return resp


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
