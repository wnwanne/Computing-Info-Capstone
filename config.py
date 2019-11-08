import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://admin:adminadmin@database-capstone.cyzqwbhouut1.us-east-1.rds.amazonaws.com/Capstone'
        # os.environ.get('DATABASE_URL') or \
        # 'sqlite:///' + os.path.join(basedir, 'app.db')


    SQLALCHEMY_TRACK_MODIFICATIONS = False