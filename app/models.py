import os
import requests
import time
from datetime import datetime, timedelta
from flask import current_app, render_template
from sqlalchemy.orm import backref
from bs4 import BeautifulSoup
from app import db
from app.search import add_to_index, remove_from_index, query_index

COMPANY_INFO_URL = 'https://www.bursamalaysia.com/trade/trading_resources/listing_directory/company-profile?stock_code='
COMPANY_TRADE_URL = 'https://www.bursamalaysia.com/market_information/equities_prices?sort_by=short_name&sort_dir=asc&per_page=50&page='
ANNOUNCEMENT_SEARCH_URL = 'https://www.bursamalaysia.com/market_information/announcements/company_announcement?keyword&per_page=50&page=1&company='
ANNOUNCEMENT_INFO_URL = 'https://disclosure.bursamalaysia.com/FileAccess/viewHtml?e='

class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)

db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)

subscribe = db.Table('subscribe',
    db.Column('telegram_id', db.Integer, db.ForeignKey('telegram_subscriber.id')),
    db.Column('company_id', db.Integer, db.ForeignKey('company.id'))
)

class Company(SearchableMixin, db.Model):
    __searchable__ = ['stock_code', 'stock_name', 'company_name']
    id = db.Column(db.Integer, primary_key=True)
    stock_code = db.Column(db.String(8), index=True, unique=True, nullable=False)
    stock_name = db.Column(db.String(32), index=True, nullable=False)
    company_name = db.Column(db.String(128), index=True, nullable=False)
    company_site = db.Column(db.String(256))
    market = db.Column(db.String(32), nullable=False)
    sector = db.Column(db.String(64), nullable=False)
    announcement = db.relationship('Announcement', backref='announced_company', lazy='dynamic', order_by='desc(Announcement.announced_date)')
    subscriber = db.relationship('TelegramSubscriber', secondary=subscribe, back_populates='subscribed_company', lazy='dynamic')

    def __repr__(self):
        return '<Company {}>'.format(self.stock_name)

    @staticmethod
    def company_message(companies, message=None):
        return render_template('telebot/company_template.html', message=message, companies=companies, company_url=COMPANY_INFO_URL)

    @staticmethod
    def company_scrape():
        companies = []

        try:
            stock_source = requests.get(COMPANY_TRADE_URL)
        except:
            return "Stock source cannot be found."
        stock_soup = BeautifulSoup(stock_source.text, 'lxml')

        total_pages = int(stock_soup.find('li', {'id': "total_page"})['data-val'])

        for page in range(1, total_pages+1):
            try:
                stock_source = requests.get(COMPANY_TRADE_URL+str(page))
            except:
                print("page missing..." + str(page))
                continue
            stock_soup = BeautifulSoup(stock_source.text, 'lxml')
            stock_results = stock_soup.find('table').find('tbody', class_="font-xsmall").find_all('tr')
            for stock_result in stock_results:
                stock_code = stock_result.find_all('td')[2].text.strip()
                print("examining stock_code..."+stock_code)
                if Company.query.filter_by(stock_code=stock_code).first():
                    continue
                stock_name = stock_result.find_all('td')[1].text.strip().split(' ')[0]
                last_done = stock_result.find_all('td')[4].text.strip()
                volume = stock_result.find_all('td')[8].text.strip()

                # Request the site's HTML in text format then render in lxml markup
                company_info = COMPANY_INFO_URL + stock_code
                try:
                    company_source = requests.get(company_info)
                except:
                    return "Company source cannot be found."
                company_soup = BeautifulSoup(company_source.text, 'lxml')

                try:
                    company_site = company_soup.find('a', {'target': '_blank'}, class_='btn btn-block btn-effect btn-white').get('href')
                except:
                    company_site = ""
                finally:
                    company_name = company_soup.find('h5', class_='bold text-muted my-2 clear-line-height').text
                    market = company_soup.find('label', text='Market:').next_sibling.strip()
                    sector = company_soup.find('label', text='Sector:').next_sibling.strip()
                    company = Company(
                            stock_code = stock_code,
                            stock_name = stock_name,
                            company_name = company_name,
                            company_site = company_site,
                            market = market,
                            sector = sector
                            )
                    companies.append(company)
                    db.session.add(company)

            progress = round(page/total_pages*100, 2)
            print('\r{}% done...'.format(progress), end='', flush=True)

        return companies

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(128))
    announced_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ann_id = db.Column(db.String(16), unique=True, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    title = db.Column(db.String(1024))

    def __repr__(self):
        return '<Announcement {}>'.format(self.title)

    def subscriber(self):
        return TelegramSubscriber.query.join(subscribe, (subscribe.c.telegram_id == TelegramSubscriber.id)).filter(subscribe.c.company_id == self.company_id).order_by(TelegramSubscriber.chat_id.asc()).all()

    def announcement_message(self):
        just_in = False
        if self.announced_date >= datetime.now() - timedelta(days=1):
            just_in = True
        try:
            announced_company = self.announced_company.company_name
            announced_company_code = self.announced_company.stock_code
        except:
            announced_company = None
            announced_company_code = None
        host_url = os.environ.get('HOST_URL')
        announcement_input = {
                'just_in': just_in,
                'announced_company': announced_company,
                'announced_company_code': announced_company_code,
                'announcement_title': self.title,
                'announced_date': str(self.announced_date.date().strftime('%d/%m/%Y')),
                'ann_id': self.ann_id,
                'host_url': host_url,
                'company_url': COMPANY_INFO_URL
                }
        return render_template('telebot/announcement_template.html', announcement_input=announcement_input)

    @staticmethod
    def announcement_scrape(extract_latest=True):
        announcements = []
        stocks = []

        if len(Company.query.all()) == 0:
            Company.company_scrape()

        if extract_latest:
            stocks.append('')
        else:
            for stock in Company.query.all():
                stocks.append(stock.stock_code)

        stock_ind = 0
        while True:
            stock = stocks[stock_ind]
            announcement_search = ANNOUNCEMENT_SEARCH_URL + stock

            # Request the site's HTML in text format then render in lxml markup
            try:
                search_source = requests.get(announcement_search)
                search_soup = BeautifulSoup(search_source.text, 'lxml')
            except:
                return "Search source cannot be found."

            try:
                announcement_list = search_soup.find("table", {"id": "table-announcements"}).find('tbody').find_all('tr')[:20]
                for announce in announcement_list:
                    announce_row = announce.find_all('td')
                    try:
                        stock_code = announce_row[2].find('a').get('href').split('=')[1]
                    except:
                        stock_code = ''
                    ann_id = announce_row[3].find('a').get('href').split('=')[1]
                    if Announcement.query.filter_by(ann_id=ann_id).first():
                        continue
                    announcement_date = announce_row[1].text.strip()
                    announcement_details = announce_row[3].find('a').text.strip()
                    if announce_row[3].find('span'):
                        announcement_details += ' ' + announce_row[3].find('span').text.strip()
                    if announce_row[3].find('p'):
                        announcement_details += " - " + announce_row[3].find('p').text.strip().replace('\t',' ').replace('\n',' ').replace('\r','')
                    announcement_info = ANNOUNCEMENT_INFO_URL + ann_id
                    info_source = requests.get(announcement_info)
                    info_soup = BeautifulSoup(info_source.text, 'lxml')
                    announcement_cat = info_soup.find("div", class_="ven_announcement_info").find('table').find_all('tr')
                    for ann_cat in announcement_cat:
                        category = ann_cat.find('td', text='Category')
                        if category:
                            category = category.find_next('td').text.strip()
                            break
                    announcement = Announcement(
                            category = category,
                            announced_date = datetime.strptime(announcement_date, '%d %b %Y'),
                            ann_id = ann_id,
                            announced_company = Company.query.filter_by(stock_code=stock_code).first(),
                            title = announcement_details
                            )
                    announcements.append(announcement)
                    # db.session.add(announcement)
                print("List of announcements sending: ", announcements)
            except:
                print('No information extracted for stock code ' + stock)

            if stock_ind == len(stocks)-1:
                break
            else:
                stock_ind += 1
                progress = round(stock_ind/(len(stocks)-1)*100, 2)

        announcements.reverse()
        return announcements

class TelegramSubscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, index=True, unique=True, nullable=False)
    joined_datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    subscribed_company = db.relationship('Company', secondary=subscribe, order_by='Company.stock_name', back_populates='subscriber', lazy='dynamic')

    def __repr__(self):
        return '<TelegramSubscriber {}>'.format(self.chat_id)

    def subscribes(self, company):
        if not self.has_subscribed(company):
            self.subscribed_company.append(company)

    def unsubscribes(self, company):
        if self.has_subscribed(company):
            self.subscribed_company.remove(company)

    def optout(self):
        subbed_company = self.subscribed_company.all()
        for sub in subbed_company:
            self.unsubscribes(sub)
        db.session.delete(self)

    def has_subscribed(self, company):
        return self.subscribed_company.filter(subscribe.c.company_id == company.id).count() > 0

    def subscribed_announcements(self):
        return Announcement.query.join(subscribe, (subscribe.c.company_id == Announcement.company_id)).filter(subscribe.c.telegram_id == self.id).order_by(Announcement.announced_date.desc()).all()
