import os
from apscheduler.schedulers.blocking import BlockingScheduler
from app import db, telegram_bot
from app.models import Company, Announcement, Subscribe, TelegramSubscriber

scheduler = BlockingScheduler()

def initiate_app():
    from app import create_app
    app = create_app()
    app.app_context().push()

@scheduler.scheduled_job('cron', day_of_week='mon-fri', hour='8-19', minute='*', second='0', jitter=15, timezone='Asia/Kuala_Lumpur')
def data_loading():
    initiate_app()

    # Load company (qoute) details and announcement details
    Company.company_scrape()
    announcements = Announcement.announcement_scrape()
    db.session.commit()

    # Send out announcements based on announcements loading
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

    # Query all companies and run price check and price alert for each
    subs = Subscribe.query.all()
    for sub in subs:
        sub.company.price_change()
        sub.company.price_alert()

    db.session.commit()

@scheduler.scheduled_job('cron', day_of_week='mon-sun', hour='3', minute='0', second='0', timezone='Asia/Kuala_Lumpur')
def announcement_cleaning():
    initiate_app()
    Announcement.announcement_cleaning()
    db.session.commit()

@scheduler.scheduled_job('cron', day_of_week='mon-fri', hour='18', minute='30', timezone='Asia/Kuala_Lumpur')
def daily_update():
    initiate_app()
    users = TelegramSubscriber.query.filter_by(status=1).all()
    for user in users:
        user.daily_update()
    db.session.commit()

if __name__ == "__main__":
    scheduler.start()

