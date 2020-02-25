from bs4 import BeautifulSoup
import requests
from flask import current_app
from app import db
from app.models import Company, Announcement
from datetime import datetime
import time

COMPANY_INFO_URL = 'https://www.bursamalaysia.com/trade/trading_resources/listing_directory/company-profile?stock_code='
COMPANY_TRADE_URL = 'https://www.bursamalaysia.com/market_information/equities_prices?sort_by=short_name&sort_dir=asc&per_page=50&page='
ANNOUNCEMENT_SEARCH_URL = 'https://www.bursamalaysia.com/market_information/announcements/company_announcement?keyword&per_page=50&page=1&company='
ANNOUNCEMENT_INFO_URL = 'https://disclosure.bursamalaysia.com/FileAccess/viewHtml?e='

def company_scrape():
    companies = []

    try:
        stock_source = requests.get(COMPANY_TRADE_URL)
    except:
        return "Stock source cannot be found."
    stock_soup = BeautifulSoup(stock_source.text, 'lxml')

    total_pages = int(stock_soup.find('ul', class_="pagination").find_all('li')[-2].find('a').text.strip())

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
            if Company.query.filter_by(stock_code=stock_code).first():
                continue
            stock_name = stock_result.find_all('td')[1].text.strip().split(' ')[0]
            last_done = stock_result.find_all('td')[4].text.strip()
            volume = stock_result.find_all('td')[8].text.strip()
            company_info = COMPANY_INFO_URL + stock_code

            # Request the site's HTML in text format then render in lxml markup
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

def announcement_scrape(extract_latest=True):
    announcements = []
    stocks = []

    if len(Company.query.all()) == 0 and not extract_latest:
        return "Method not allowed."
    elif extract_latest:
        stocks.append('')
    elif not extract_latest:
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
                stock = announce_row[2].find('a').get('href').split('=')[1]
                ann_id = announce_row[3].find('a').get('href').split('=')[1]
                if Announcement.query.filter_by(ann_id=ann_id).first():
                    continue
                announcement_date = announce_row[1].text.strip()
                announcement_details = announce_row[3].find('a').text.strip()
                announcement_details += " - " + announce_row[3].find('p').text.strip().replace('\t',' ').replace('\n',' ').replace('\r','')
                announcement_info = ANNOUNCEMENT_INFO_URL + ann_id
                info_source = requests.get(announcement_info)
                info_soup = BeautifulSoup(info_source.text, 'lxml')
                announcement_cat = info_soup.find("div", class_="ven_announcement_info").find('table').find_all('tr')[3].find_all('td')[1].text.strip()
                announcement = Announcement(
                        category = announcement_cat,
                        announced_date = datetime.strptime(announcement_date, '%d %b %Y'),
                        ann_id = ann_id,
                        announced_company = Company.query.filter_by(stock_code=stock).first(),
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
            print('\r{}% done...'.format(progress), end='', flush=True)

    return announcements
