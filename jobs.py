import os
import datetime
import time
from flask import current_app
from apscheduler.schedulers.blocking import BlockingScheduler
from app import create_app, db, telegram_bot
from app.models import Company, Announcement, Subscribe, TelegramSubscriber

app = create_app()
scheduler = BlockingScheduler()

@scheduler.scheduled_job('cron', day_of_week='mon-fri', hour='8-19', minute='*/10', second='15', jitter=15, timezone='Asia/Kuala_Lumpur')
def data_loading():
    app.app_context().push()

    # Load company (quote) details and announcement details
    print("Starting data loading job...")
    #Company.company_scrape()
    announcements = Announcement.announcement_scrape()
    db.session.commit()

    if not Announcement.query.filter_by(announced_date=datetime.date.today()).first():
        print("No operation today, no announcement/stock update required")
        return

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
                time.sleep(0.1)
                telegram_bot.send_message(chat_id=chat, text=response, parse_mode='HTML')

    # Query all companies and run price check and price alert for each
    subs = Subscribe.query.all()
    for sub in subs:
        sub.company.price_change()
        sub.company.price_alert()

    db.session.commit()
    print("Data loading job completed...")

@scheduler.scheduled_job('cron', day_of_week='mon-sun', hour='22', minute='0', second='0', timezone='Asia/Kuala_Lumpur')
def cleaning():
    print("Starting cleaning job...")
    app.app_context().push()
    Company.company_cleaning()
    Announcement.announcement_cleaning()
    db.session.commit()
    print("Cleaning job completed...")

@scheduler.scheduled_job('cron', day_of_week='mon-fri', hour='18', minute='30', timezone='Asia/Kuala_Lumpur')
def daily_update():
    app.app_context().push()
    if not Announcement.query.filter_by(announced_date=datetime.date.today()).first():
        print("No operation today, no daily update required...")
        return

    print("Starting daily update job...")
    users = TelegramSubscriber.query.filter_by(status=1).all()
    for user in users:
        user.daily_update()
    db.session.commit()
    print("Daily update job completed...")

if __name__ == "__main__":
    scheduler.start()
