from apscheduler.schedulers.blocking import BlockingScheduler
from app.helpers.scrape import company_scrape, announcement_scrape
from app.helpers.telebot_jobs import send_new_announcement
from app import db

scheduler = BlockingScheduler()

@scheduler.scheduled_job('cron', day_of_week='mon-fri', hour='8-20', minute='0-59', second='0-59/10', timezone='Asia/Kuala_Lumpur')
def annscrape():
    announcements = announcement_scrape()
    db.session.commit()
    sentStatus = send_new_announcement(announcements)

@scheduler.scheduled_job('cron', day_of_week='mon-fri', hour=8, timezone='Asia/Kuala_Lumpur')
def compscrape():
    company_list = company_scrape()
    db.session.commit()

scheduler.start()
