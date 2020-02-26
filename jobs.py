from apscheduler.schedulers.blocking import BlockingScheduler
from app.helpers.scrape import company_scrape, announcement_scrape
from app.helpers.telebot_jobs import send_new_announcement
from app import db
from app.models import Company

scheduler = BlockingScheduler()

@scheduler.scheduled_job('cron', day_of_week='mon-fri', hour='8-20', minute='0-59', second='0-59/10', timezone='Asia/Kuala_Lumpur')
def annscrape():
    from app import create_app
    app = create_app()
    app.app_context().push()

    if len(Company.query.all()) == 0:
        compscrape()

    announcements = announcement_scrape()
    print(announcements)
    db.session.commit()
    sentStatus = send_new_announcement(announcements)
    return "Annscrape done"

@scheduler.scheduled_job('cron', day_of_week='mon-fri', hour='7,19', timezone='Asia/Kuala_Lumpur')
def compscrape():
    from app import create_app
    app = create_app()
    app.app_context().push()

    company_list = company_scrape()
    db.session.commit()
    return "Compscrape done"

scheduler.start()
