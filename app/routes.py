import logging
import numpy as np
from nba_api.stats.static import teams
from nba_api.stats.static import players
from nba_api.stats.endpoints import leaguegamefinder
import pandas as pd
import requests
from app import db
from flask import current_app as app
from app.forms import LoginForm, RegistrationForm, SearchForm
from app.models import User
import flask
from flask import render_template, flash, redirect, url_for, request, \
    session, Blueprint
from flask_login import current_user, login_user, logout_user, login_required
from twilio.rest import Client
from werkzeug.urls import url_parse

bp = Blueprint('main', __name__)

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    team_names = []
    f = open('teams.txt', 'r')
    for line in f:
        team_names.append(line.strip('\n'))
    return render_template('index.html', title='Home', team_names=team_names)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username  or  password')
            return redirect(url_for('main.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data,
                    phone_number=form.phone_number.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        session['phone'] = form.phone_number.data
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Register', form=form)


@bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    form = SearchForm()
    team_names = []
    f = open('teams.txt', 'r')
    for line in f:
        team_names.append(line.strip('\n'))
    it = iter(team_names)
    team_names = zip(it, it)
    form.team.choices = team_names

    # flash(fav_short_team)
    return render_template('search.html', title='Search', form=form)


@bp.route('/search/sending', methods=['GET', 'POST'])
@login_required
def sending():

    form = SearchForm()
    phone = session.get('phone')

    if form.validate_on_submit:
        fav_short_team = flask.request.values.get('team')

        url = "https://api-nba-v1.p.rapidapi.com/teams/shortName/{}".\
            format(fav_short_team)

        headers = {
            'x-rapidapi-host': "api-nba-v1.p.rapidapi.com",
            'x-rapidapi-key': "acca717e1fmshd937604fdb1e291p148866jsn0e6ec8ccd90e"
        }

        # API Call
        response = requests.request("GET", url, headers=headers)

        # API Response as JSON
        team_json = response.json()

        # Find Stats
        team_name = team_json['api']['teams'][0]['fullName']
        nba_teams = teams.find_teams_by_full_name(team_name)
        team_id = nba_teams[0]['id']
        game_finder = leaguegamefinder.LeagueGameFinder(team_id_nullable=team_id)
        games = game_finder.get_data_frames()[0]

        # Narrow down list of stats and to latest season
        games_1819 = games[games.SEASON_ID.str[-4:] == '2018']
        cols = ['TEAM_NAME', 'GAME_ID', 'GAME_DATE', 'MATCHUP', 'WL',
                'MIN', 'PTS', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT',
                'FTM', 'FTA', 'FT_PCT', 'OREB', 'DREB', 'REB', 'AST', 'STL', 'BLK', 'TOV',
                'PF', 'PLUS_MINUS']
        games_1819 = games_1819[cols]
        team_stats = games_1819.mean()
        team_name = games_1819['TEAM_NAME'].to_list()[0]

        # Twilio access tokens used to send SMS
        # ADD AUTHENTICATION
        # *******************************************
        acc_sid = ''
        auth_token = ''
        client = Client(acc_sid, auth_token)
        # *******************************************
        # SMS message sent
        Message = 'SEASON STATS: Team Name: {}, Minutes Played: {}, PTS: {}, FGM: {}, FGA: {}, ' \
                  'FG_PCT {}, FG3M {}, FG3A {}, FG3_PCT {}, FTM {}, FTA {}, FT_PCT {}, OREB {}, DREB {}, REB {}, AST {}, ' \
                  'STL {}, BLK {}, TOV {}, PF {}, PLUS_MINUS {}'.format(team_name, round(team_stats['MIN'], 2),
                                                                        round(team_stats['PTS'], 2),
                                                                        round(team_stats['FGM'], 2),
                                                                        round(team_stats['FGA'], 2),
                                                                        round(team_stats['FG_PCT'], 2),
                                                                        round(team_stats['FG3M'], 2),
                                                                        round(team_stats['FG3A'], 2),
                                                                        round(team_stats['FG3_PCT'], 2),
                                                                        round(team_stats['FTM'], 2),
                                                                        round(team_stats['FTA'], 2),
                                                                        round(team_stats['FT_PCT'], 2),
                                                                        round(team_stats['OREB'], 2),
                                                                        round(team_stats['DREB'], 2),
                                                                        round(team_stats['REB'], 2),
                                                                        round(team_stats['AST'], 2),
                                                                        round(team_stats['STL'], 2),
                                                                        round(team_stats['BLK'], 2),
                                                                        round(team_stats['TOV'], 2),
                                                                        round(team_stats['PF'], 2),
                                                                        round(team_stats['PLUS_MINUS'], 2))
        message = client.messages.create(to=phone,
                                         from_='8622256658',
                                         body=Message)

        flash("Sending stats... for " + fav_short_team)
        return redirect(url_for('main.index'))

    return render_template('search.html', title='Search', form=form)
