from app.models import Announcement, Company, TelegramSubscriber

def get_company(stock):
    # To get single company object from stock in string
    queried_company = Company.query.filter_by(stock_name=stock).first()
    return queried_company

def get_announcements(stock, limit=10):
    # To get list of announcement objects according to company string
    queried_company = get_company(stock)
    queried_announcements = Announcement.query.filter_by(announced_company=queried_company).order_by(Announcement.id).limit(limit).all()
    return queried_announcements

def get_subscribing(chat_id):
    # To get list of subscribing company objects according to chat_id in string
    pass
