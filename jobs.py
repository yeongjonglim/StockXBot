import os
from apscheduler.schedulers.blocking import BlockingScheduler
from app import db, telegram_bot
from app.models import Company, Announcement

scheduler = BlockingScheduler()

def initiate_app():
    from app import create_app
    app = create_app()
    app.app_context().push()

@scheduler.scheduled_job('cron', day_of_week='mon-fri', hour='8-12,13-19', minute='0-59', second='0', timezone='Asia/Kuala_Lumpur')
def annscrape():
    initiate_app()
    announcements = Announcement.announcement_scrape()
    db.session.commit()
    for announcement in announcements:
        recipients = announcement.subscriber()
        chats = []
        for recipient in recipients:
            chats.append(recipient.chat_id)
        chats.append(os.environ.get('TARGET_CHANNEL'))

        response = announcement.announcement_message()
        if response:
            for chat in chats:
                print("Sending to ..." + str(chat))
                telegram_bot.send_message(chat_id=chat, text=response, parse_mode='HTML')

@scheduler.scheduled_job('cron', day_of_week='mon-sun', hour='3', minute='0', second='0', timezone='Asia/Kuala_Lumpur')
def anncleaning():
    initiate_app()
    Announcement.announcement_cleaning()
    db.session.commit()

@scheduler.scheduled_job('cron', day_of_week='mon-fri', hour='7', timezone='Asia/Kuala_Lumpur')
def compscrape():
    initiate_app()
    company_list = Company.company_scrape()
    db.session.commit()

scheduler.start()

