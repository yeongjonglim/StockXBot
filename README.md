# StockXBot

This is a bot to notify users on latest stock announcements and price alerts.

## Deployment

Deployed on [Heroku](https://heroku.com).

## Built With

* [Flask](https://flask.palletsprojects.com/en/1.1.x/) - Main frame to connect the messenger, database and any other API.
* [APScheduler](https://apscheduler.readthedocs.io/en/stable/) - Cron type scheduler to schedule jobs to check for announcements and prices.
* [DialogFlow](https://cloud.google.com/dialogflow/docs) - Natural Language Processing to understand the user's intends.
* [Telegram](https://python-telegram-bot.readthedocs.io/en/stable/) - Current messenger used.

## Acknowledgements

Inspired By: [Stockbot.sg](http://stockbot.sg)
