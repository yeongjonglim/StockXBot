import os
import requests
import time
import datetime
from flask import current_app, render_template
from sqlalchemy import and_
from sqlalchemy.orm import backref
from sqlalchemy.ext.associationproxy import association_proxy
from bs4 import BeautifulSoup
from app import db, telegram_bot
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

class Subscribe(db.Model):
    __tablename__ = 'subscribe'
    telegram_id = db.Column(db.Integer, db.ForeignKey('telegram_subscriber.id'), primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), primary_key=True)
    subscribed_datetime = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    price_alert = db.Column(db.Float)
    price_alert_status = db.Column(db.Integer, default=0) # Status 0: Price alert not fulfilled, Status 1: Price alert fulfilled
    last_sent = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_update = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    telegram_subscriber = db.relationship('TelegramSubscriber', backref=backref("subscribe", cascade="all, delete-orphan"))
    company = db.relationship('Company', backref=backref("subscribe", cascade="all, delete-orphan"), order_by="Company.stock_name", lazy="joined", innerjoin=True)

    def __repr__(self):
        return '<User {} subscribe {}>'.format(self.telegram_id, self.company_id)

    def user_notified(self):
        time_now = datetime.datetime.utcnow()
        self.last_sent = time_now

    def set_price_alert(self, price):
        time_now = datetime.datetime.utcnow()
        self.price_alert = price
        self.price_alert_status = 0
        self.last_update = time_now

    def price_alert_notified(self):
        self.price_alert_status = 1
        self.user_notified()

class Company(SearchableMixin, db.Model):
    __tablename__ = 'company'
    __searchable__ = ['stock_code', 'stock_name', 'company_name']
    id = db.Column(db.Integer, primary_key=True)
    stock_code = db.Column(db.String(8), index=True, unique=True, nullable=False)
    stock_name = db.Column(db.String(32), unique=True, nullable=False)
    company_name = db.Column(db.String(128), nullable=False)
    company_site = db.Column(db.String(256), nullable=True)
    market = db.Column(db.String(32), nullable=False)
    sector = db.Column(db.String(64), nullable=False)
    last_done = db.Column(db.Float, nullable=True)
    change_absolute = db.Column(db.Float, nullable=True)
    change_percent = db.Column(db.Float, nullable=True)
    opening = db.Column(db.Float, nullable=True)
    closing = db.Column(db.Float, nullable=True)
    volume = db.Column(db.Integer, nullable=True)
    last_update = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    announcement = db.relationship('Announcement', backref='announced_company', lazy='dynamic', order_by='desc(Announcement.announced_date)')
    subscriber = association_proxy('subscribe', 'telegram_subscriber')

    def __repr__(self):
        return '<Company {}>'.format(self.stock_name)

    def price_change(self, max_send_frequency=2):
        # Storing current utc datetime
        datetime_now = datetime.datetime.utcnow()
        target_time = datetime_now - datetime.timedelta(hours=max_send_frequency)

        if abs(self.change_percent) >= 3:
            # Query list of subscribers that received price alerts more than max_send_frequency hours ago for self(company)
            users = TelegramSubscriber.query.filter(TelegramSubscriber.subscribe.any(and_(Subscribe.last_sent<=target_time, Subscribe.company_id==self.id))).all()
            for user in users:
                response = render_template('telebot/price_alert.html', header='Volatile Alert', company=self, user=user, company_url=COMPANY_INFO_URL)
                telegram_bot.send_message(chat_id=user.chat_id, text=response, parse_mode='HTML')
                sub = Subscribe.query.filter(Subscribe.telegram_id == user.id, Subscribe.company_id == self.id).first()
                sub.user_notified()

    def price_alert(self, max_send_frequency=2):
        # Storing current utc datetime
        datetime_now = datetime.datetime.utcnow()
        target_time = datetime_now - datetime.timedelta(hours=max_send_frequency)

        subscription = Subscribe.query.filter(Subscribe.company_id == self.id, Subscribe.last_sent<=target_time, Subscribe.price_alert_status == 0, Subscribe.price_alert != None).all()
        for sub in subscription:
            if abs(self.last_done - sub.price_alert) < 0.005:
                user = TelegramSubscriber.query.filter(TelegramSubscriber.id==sub.telegram_id).first()
                response = render_template('telebot/price_alert.html', header='Price Alert', company=self, user=user, company_url=COMPANY_INFO_URL)
                telegram_bot.send_message(chat_id=user.chat_id, text=response, parse_mode='HTML')
                sub.price_alert_notified()

    @staticmethod
    def check_quote(string):
        if string == '-':
            return float(0)
        else:
            return float(string)

    @staticmethod
    def company_message(companies, message=None):
        return render_template('telebot/company_template.html', message=message, companies=companies, company_url=COMPANY_INFO_URL)

    @staticmethod
    def company_scrape():
        companies = []

        # Storing current time for Malaysia's timezone
        tz = datetime.timezone(datetime.timedelta(hours=8))
        time_now = datetime.datetime.now(tz).time()

        # Morning refresh timing
        time_start = datetime.time(8, 00)
        time_end = datetime.time(8, 30)

        try:
            stock_source = requests.get(COMPANY_TRADE_URL)
        except:
            print("Stock source cannot be found.")
            return companies
        stock_soup = BeautifulSoup(stock_source.text, 'lxml')

        total_pages = int(stock_soup.find('li', {'id': "total_page"})['data-val'])

        print("Scraping company information...")
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
                stock_name = stock_result.find_all('td')[1].text.strip().split(' ')[0]
                last_done = Company.check_quote(stock_result.find_all('td')[4].text.strip())
                closing = Company.check_quote(stock_result.find_all('td')[5].text.strip())
                change_absolute = last_done - closing if last_done != 0.0 else float(0)
                change_percent = (change_absolute / closing)*100
                volume = int(Company.check_quote(stock_result.find_all('td')[8].text.strip().replace(',', ''))*100)

                # Initialising variables
                company_site = None
                company_name = None
                market = None
                sector = None
                opening = None

                if not Company.query.filter_by(stock_code=stock_code).first() or (time_now >= time_start and time_now < time_end):
                    # Request the site's HTML in text format then render in lxml markup
                    company_info = COMPANY_INFO_URL + stock_code
                    try:
                        company_source = requests.get(company_info)
                        company_soup = BeautifulSoup(company_source.text, 'lxml')
                    except:
                        print("Company source cannot be found.")
                        continue

                    try:
                        company_site = company_soup.find('a', {'target': '_blank'}, class_='btn btn-block btn-effect btn-white').get('href')
                    except:
                        company_site = ""
                    finally:
                        company_name = company_soup.find('h5', class_='bold text-muted my-2 clear-line-height').text
                        market = company_soup.find('label', text='Market:').next_sibling.strip()
                        sector = company_soup.find('label', text='Sector:').next_sibling.strip()
                        opening = Company.check_quote(company_soup.find('th', text='Open').find_next('td').text.strip())

                if Company.query.filter_by(stock_code=stock_code).first():
                    data = {
                        'last_done': last_done,
                        'closing': closing,
                        'change_absolute': change_absolute,
                        'change_percent': change_percent,
                        'volume': volume,
                        'last_update': datetime.datetime.utcnow()
                    }
                    if company_site:
                        data['company_site'] = company_site
                    if market:
                        data['market'] = market
                    if sector:
                        data['sector'] = sector
                    if opening:
                        data['opening'] = opening

                    Company.query.filter_by(stock_code=stock_code).update(data)
                else:
                    company = Company(
                            stock_code = stock_code,
                            stock_name = stock_name,
                            company_name = company_name,
                            company_site = company_site,
                            market = market,
                            sector = sector,
                            last_done = last_done,
                            opening = opening,
                            closing = closing,
                            change_absolute = change_absolute,
                            change_percent = change_percent,
                            volume = volume
                            )
                    db.session.add(company)
                    companies.append(company)

        return companies

class Announcement(db.Model):
    __tablename__ = 'announcement'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(128))
    announced_date = db.Column(db.Date, nullable=False, default=datetime.date.today)
    ann_id = db.Column(db.String(16), unique=True, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    title = db.Column(db.String(1024))

    def __repr__(self):
        return '<Announcement {}>'.format(self.title)

    def subscriber(self):
        return TelegramSubscriber.query.join(Subscribe, (Subscribe.telegram_id == TelegramSubscriber.id)).filter(Subscribe.company_id == self.company_id).all()

    def announcement_message(self):
        just_in = self.announced_date >= (datetime.datetime.now() - datetime.timedelta(days=1)).date()
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
                'announced_date': str(self.announced_date.strftime('%d/%m/%Y')),
                'ann_id': self.ann_id,
                'host_url': host_url,
                'company_url': COMPANY_INFO_URL
                }
        return render_template('telebot/announcement_template.html', announcement_input=announcement_input)

    @staticmethod
    def announcement_cleaning(backlog_days=10):
        delete_date = datetime.datetime.now() - datetime.timedelta(days=backlog_days)
        delete_date = delete_date.replace(hour=0, minute=0, second=0, microsecond=0)
        anns = Announcement.query.filter_by(announced_date=delete_date).all()
        for ann in anns:
            db.session.delete(ann)

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
                            announced_date = datetime.datetime.strptime(announcement_date, '%d %b %Y'),
                            ann_id = ann_id,
                            announced_company = Company.query.filter_by(stock_code=stock_code).first(),
                            title = announcement_details
                            )
                    announcements.append(announcement)
                    db.session.add(announcement)
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
    __tablename__ = 'telegram_subscriber'
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, index=True, unique=True, nullable=False)
    joined_datetime = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    username = db.Column(db.String, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    status = db.Column(db.Integer, nullable=True, default=1) # Status 0: Inactive, Status 1: Active, Status 2: Pending Feedback
    subscribed_company = association_proxy('subscribe', 'company', creator=lambda company: Subscribe(company=company))

    def __repr__(self):
        return '<TelegramSubscriber {}>'.format(self.chat_id)

    def subscribes(self, company):
        if not self.has_subscribed(company):
            self.subscribed_company.append(company)

    def unsubscribes(self, company):
        if self.has_subscribed(company):
            self.subscribed_company.remove(company)

    def has_subscribed(self, company):
        return len(Subscribe.query.filter(Subscribe.company_id==company.id, Subscribe.telegram_id==self.id).all()) > 0

    def set_price_alert(self, company, price):
        subscription = Subscribe.query.filter(Subscribe.telegram_id==self.id, Subscribe.company_id==company.id).first()
        subscription.set_price_alert(price)

    def daily_update(self):
        subscription = Subscribe.query.filter(Subscribe.telegram_id==self.id).all()
        for sub in subscription:
            comp = Company.query.filter(Company.id==sub.company_id).first()
            response = render_template('telebot/price_alert.html', header='Daily Update', company=comp, user=self, company_url=COMPANY_INFO_URL)
            telegram_bot.send_message(chat_id=self.chat_id, text=response, parse_mode='HTML')
            sub.user_notified()

    def optout(self):
        for i in range(len(self.subscribed_company)):
            self.unsubscribes(comps[0])
        self.status = 2

    def activate(self):
        self.status = 1

    def deactivate(self):
        self.status = 0

    def update_name(self, chat):
        self.username = chat.username
        self.first_name = chat.first_name
        self.last_name = chat.last_name

    def subscribed_announcements(self):
        return Announcement.query.join(Subscribe, (Subscribe.company_id == Announcement.company_id)).filter(Subscribe.telegram_id == self.id).order_by(Announcement.announced_date.desc()).all()
