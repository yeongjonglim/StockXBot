import os
from apscheduler.schedulers.blocking import BlockingScheduler
from app import db
from app.models import Company, Announcement
from app.telebot.helper import send_telegram

scheduler = BlockingScheduler()

@scheduler.scheduled_job('cron', day_of_week='mon-fri', hour='8-21', minute='0-59', second='0-59/10', timezone='Asia/Kuala_Lumpur')
def annscrape():
    from app import create_app
    app = create_app()
    app.app_context().push()

    announcements = Announcement.announcement_scrape()
    print(announcements)
    db.session.commit()
    for announcement in announcements:
        recipients = announcement.subscriber()
        chats = []
        for recipient in recipients:
            chats.append(recipient.chat_id)
        chats.append(os.environ.get('TARGET_CHANNEL'))
        send_telegram(objects=[announcement], chat_id=chats, message_function=Announcement.announcement_message)
    return "Annscrape done"

@scheduler.scheduled_job('cron', day_of_week='mon-fri', hour='7', timezone='Asia/Kuala_Lumpur')
def compscrape():
    from app import create_app
    app = create_app()
    app.app_context().push()

    company_list = Company.company_scrape()
    db.session.commit()
    return "Compscrape done"

scheduler.start()
