from flask import render_template, redirect, url_for
from app.main import bp
# from app.helpers.scrape import company_scrape, announcement_scrape
# from app.helpers.telebot_jobs import sendNewAnnouncement
from app.models import Company
from app import db

@bp.route('/', methods=['GET'])
def index():
    return render_template('index.html', title='Home')

@bp.route('/scrape', methods=['GET'])
def scrape():
    # company_list = company_scrape()
    # print(company_list)
    # db.session.commit()
    return redirect(url_for('.index'))

@bp.route('/annscrape', methods=['GET'])
def annscrape():
    # announcements = announcement_scrape()
    # db.session.commit()
    # print(announcements)
    # sentStatus = sendNewAnnouncement(announcements)
    # print(sentStatus)
    return redirect(url_for('.index'))
