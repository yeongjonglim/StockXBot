import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    # App default config
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'StockXBot'

    # Logging config
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT') or None

    # DB config
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Elasticsearch config
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')

    # Mail config
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = [os.environ.get('ADMIN_EMAIL')]
