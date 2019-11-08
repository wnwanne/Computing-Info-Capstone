import logging
from nba_api.stats.static import teams
from nba_api.stats.static import players
from nba_api.stats.endpoints import leaguegamefinder
import requests
import urllib
import sqlalchemy
from sqlalchemy.sql import exists
import pyodbc
from app import app, db
from app.forms import LoginForm, RegistrationForm, SearchForm
from app.models import User, NBAStats
import flask
from flask import render_template, flash, redirect, url_for, request, session
from flask_login import current_user, login_user, logout_user, login_required
from twilio.rest import Client
from werkzeug.urls import url_parse


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    team_names = []
    f = open('teams.txt', 'r')
    for line in f:
        team_names.append(line.strip('\n'))
    return render_template('index.html', title='Home', team_names=team_names)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username  or  password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data,
                    phone_number=form.phone_number.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        session['phone'] = form.phone_number.data
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    # opens teams list and sets up dropdown
    form = SearchForm()
    team_names = []
    f = open('teams.txt', 'r')
    for line in f:
        team_names.append(line.strip('\n'))
    it = iter(team_names)
    team_names = zip(it, it)
    form.team.choices = team_names

    return render_template('search.html', title='Search', form=form)


@app.route('/search/saving', methods=['GET', 'POST'])
@login_required
def saving():

    form = SearchForm()
    phone = session.get('phone')

    if form.validate_on_submit:
        fav_short_team = flask.request.values.get('team')

        url = "https://api-nba-v1.p.rapidapi.com/teams/shortName/{}".\
            format(fav_short_team)

        headers = {
            'x-rapidapi-host': "api-nba-v1.p.rapidapi.com",
            'x-rapidapi-key': "5a64743a7bmsh79b17ce5d033775p102796jsneae2a4334407"
        }

        # API Call
        response = requests.request("GET", url, headers=headers)
        # API Response as JSON
        team_json = response.json()

        # Find Stats
        team_name = team_json['api']['teams'][0]['fullName']
        session['team_name'] = team_name

        #check if stats are already in DB
        it_exists = db.session.query(db.exists().where(NBAStats.TEAM_NAME == team_name)).scalar()
        if not it_exists:
            nba_stats = NBAStats(TEAM_NAME=team_name)
            db.session.add(nba_stats)
            db.session.commit()
        # nba_teams = teams.find_teams_by_full_name(team_name)
        # team_id = nba_teams[0]['id']
        # game_finder = leaguegamefinder.LeagueGameFinder(team_id_nullable=team_id)
        # games = game_finder.get_data_frames()[0]
        # games = games.to_json()
        # flash(games)

        # Narrow down list of stats and to latest season
        # games_1819 = games[games.SEASON_ID.str[-4:] == '2018']

        # cols = ['TEAM_NAME', 'GAME_ID', 'GAME_DATE', 'MATCHUP', 'WL',
        #         'MIN', 'PTS', 'FG_PCT', 'FG3_PCT', 'FT_PCT','REB', 'AST', 'STL', 'BLK', 'TOV', 'PLUS_MINUS']
        # games_1819 = games_1819[cols]
        # team_stats = games_1819.mean()

        # # Inserts team stats to db
        # db.session.add(team_stats)
        # db.session.commit()
#         # team_name = games_1819['TEAM_NAME'].to_list()[0]

#
#         #
#         #
#         #
#         #
#         # # Twilio access tokens used to send SMS
#         # # ADD AUTHENTICATION
#         # # *******************************************
#         # acc_sid = ''
#         # auth_token = ''
#         # client = Client(acc_sid, auth_token)
#         # # *******************************************
#         # # SMS message sent
#         # Message = 'SEASON STATS: Team Name: {}, Minutes Played: {}, PTS: {}, FGM: {}, FGA: {}, ' \
#         #           'FG_PCT {}, FG3M {}, FG3A {}, FG3_PCT {}, FTM {}, FTA {}, FT_PCT {}, OREB {}, DREB {}, REB {}, AST {}, ' \
#         #           'STL {}, BLK {}, TOV {}, PF {}, PLUS_MINUS {}'.format(team_name, round(team_stats['MIN'], 2),
#         #                                                                 round(team_stats['PTS'], 2),
#         #                                                                 round(team_stats['FGM'], 2),
#         #                                                                 round(team_stats['FGA'], 2),
#         #                                                                 round(team_stats['FG_PCT'], 2),
#         #                                                                 round(team_stats['FG3M'], 2),
#         #                                                                 round(team_stats['FG3A'], 2),
#         #                                                                 round(team_stats['FG3_PCT'], 2),
#         #                                                                 round(team_stats['FTM'], 2),
#         #                                                                 round(team_stats['FTA'], 2),
#         #                                                                 round(team_stats['FT_PCT'], 2),
#         #                                                                 round(team_stats['OREB'], 2),
#         #                                                                 round(team_stats['DREB'], 2),
#         #                                                                 round(team_stats['REB'], 2),
#         #                                                                 round(team_stats['AST'], 2),
#         #                                                                 round(team_stats['STL'], 2),
#         #                                                                 round(team_stats['BLK'], 2),
#         #                                                                 round(team_stats['TOV'], 2),
#         #                                                                 round(team_stats['PF'], 2),
#         #                                                                 round(team_stats['PLUS_MINUS'], 2))
#         # message = client.messages.create(to=phone,
#         #                                   from_='8622256658',
#         #                                   body=Message)
#
#         flash("Sending stats... for " + fav_short_team)

#         # return redirect(url_for('index'))
        return redirect(url_for('display'))
#
#     return render_template('search.html', title='Search', form=form)


@app.route('/display', methods=['POST', 'GET'])
@login_required
def display():
    team_name = session.get('team_name')
    team = NBAStats.query.filter_by(TEAM_NAME=team_name).first_or_404()
    name_of_team = team.TEAM_NAME
    return render_template('display.html', title='Display', display=name_of_team)