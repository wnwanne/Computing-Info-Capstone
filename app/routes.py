import logging
from nba_api.stats.static import teams
from nba_api.stats.static import players
from nba_api.stats.endpoints import leaguegamefinder
import requests
import pandas as pd
import numpy as np
import urllib
import os
import json
import sqlalchemy
from sqlalchemy.sql import exists
import pyodbc
from app import app, db
from app.forms import LoginForm, RegistrationForm, SearchForm, GSCOSearchForm
from app.models import User, NBAStats, GSCO_teams
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

@app.route('/gsco_search', methods=['GET', 'POST'])
@login_required
def gsco_search():
    # opens teams list and sets up dropdown
    form = GSCOSearchForm()
    team_names = []
    f = open('GSCO_teams.txt', 'r')
    for line in f:
        team_names.append(line.strip('\n'))
    it = iter(team_names)
    team_names = zip(it, it)
    form.gsco_team.choices = team_names
    return render_template('gsco_search.html', title='Search', form=form)


@app.route('/search/saving', methods=['GET', 'POST'])
@login_required
def saving():

    form = SearchForm()

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

        # Find Name and Logo
        team_logo = team_json['api']['teams'][0]['logo']
        team_name = team_json['api']['teams'][0]['fullName']
        #        team_ticket_price = 200  just putting this constant for now
        session['team_name'] = team_name

        # Find Average Ticket Price
        CLIENT_ID = "MTg1MDQzOTB8MTU2OTQ1MDUzNC40"

        # Format input correctly for request
        formatted_team_name = team_name.replace(" ", "+")

        # Send a request to seatgeek querying for events involving "team" and authenticating with "CLIENT_ID"
        # They will send back a json file with all of the information
        r = requests.get(
            "https://api.seatgeek.com/2/events?q=" + \
                            formatted_team_name + "&taxonomies.name=sports&type=nba&client_id=" + CLIENT_ID)

        x = json.loads(r.content)
        average_cost = 0
        games = 0
        for event in x["events"]:
            average_cost = (average_cost + int(event["stats"]["average_price"]))
            games = (games + 1)
        cost_per_game = "{0:.2f}".format(average_cost / games)

        #check if stats are already in DB
        name_exists = db.session.query(db.exists().where(NBAStats.TEAM_NAME == team_name)).scalar()
        if not name_exists:
            nba_name = NBAStats(TEAM_NAME=team_name, team_logo=team_logo, avg_price=cost_per_game)
            db.session.add(nba_name)
            db.session.commit()
        return redirect(url_for('display'))



@app.route('/GSCO_search/saving', methods=['GET', 'POST'])
@login_required
def GSCO_saving():

    form = GSCOSearchForm()

    if form.validate_on_submit:
        selected_team = flask.request.values.get('gsco_team')
        session['selected_team'] = selected_team

        # check if stats are already in DB
        name_exists = db.session.query(db.exists().where(GSCO_teams.TEAM_NAME == selected_team)).scalar()
        if not name_exists:
            token = "c7eXV50z6g4Y5wKV9o2j0LZLP76AJoR-OE9jIwOeg19XCGB6YaY"
            url_2 = "https://api.pandascore.co/csgo/teams?token={}".format(token)

            response_teams = requests.request("GET", url_2)

            teams_json = response_teams.json()

            df_teams = pd.DataFrame(teams_json)
            df_teams = df_teams.dropna(how='any', subset=['image_url'])
            new_df_teams = df_teams[['id', 'name', 'image_url']]
            selected_team_logo = new_df_teams.loc[new_df_teams['name'] == selected_team]['image_url'].values[0]
            selected_team_id = new_df_teams.loc[new_df_teams['name'] == selected_team]['id'].values[0]

            gsco_name = GSCO_teams(TEAM_NAME=selected_team, team_logo=selected_team_logo, team_id=str(selected_team_id))
            db.session.add(gsco_name)
            db.session.commit()
        return redirect(url_for('gsco_display'))


@app.route('/display', methods=['POST', 'GET'])
@login_required
def display():
    #Queries info from DB for display
    team_name = session.get('team_name')
    team = NBAStats.query.filter_by(TEAM_NAME=team_name).first_or_404()
    name_of_team = team.TEAM_NAME
    logo_of_team = team.team_logo
    ticket_price = team.avg_price
    return render_template('display2.html', title='Display', display=name_of_team,
                           logo=logo_of_team, avg_price=ticket_price)

@app.route('/gsco_display', methods=['POST', 'GET'])
@login_required
def gsco_display():
    #Queries info from DB for display
    gsco_team_name = session.get('selected_team')
    team = GSCO_teams.query.filter_by(TEAM_NAME=gsco_team_name).first_or_404()
    name_of_team = team.TEAM_NAME
    logo_of_team = team.team_logo
    return render_template('gsco_display2.html', title='Display', display=name_of_team, logo=logo_of_team)
