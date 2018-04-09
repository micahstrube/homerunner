# all the imports

import os
import sqlite3

from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash

app = Flask(__name__) # create the application instance

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE = os.path.join(app.root_path, 'homerunner.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))
app.config.from_envvar('HOMERUNNER SETTINGS', silent=True)


@app.route('/')
def show_teams():
    """Show menu of teams and players on teams"""
    db = get_db()
    cur = db.execute('select name, id from teams order by name')
    teams = cur.fetchall()
    cur = db.execute('select name, id, team_id from players order by name')
    players = cur.fetchall()
    return render_template('show_teams.html', teams=teams, players=players)


@app.route('/add_team', methods=['POST'])
def add_team():
    """Create new team"""
    db = get_db()
    db.execute('insert into teams (name) values (?)',
               [request.form['team_name']])
    db.commit()
    flash('New team {team} successfully created'.format(team=request.form['team_name']))
    return redirect(url_for('show_teams'))


@app.route('/team/<team_id>')
def team(team_id):
    """Page for team details and editing team"""
    db = get_db()
    cur = db.execute('select name, id from teams where id=?', [team_id])
    team = cur.fetchone()
    cur = db.execute('select name, id from players where team_id=(?)', [team_id])
    players = cur.fetchall()
    return render_template('team.html', team=team, players=players)


@app.route('/team/<team_id>/add_player', methods=['POST'])
def add_player_to_team(team_id):
    """Add player to specified team"""
    db = get_db()
    db.execute('insert into players (name, team_id) values (?, ?)',
               [request.form['player_name'], team_id])
    db.commit()
    flash('{player} was successfully added to team {team}'.format(player=request.form['player_name'], team=team_id))
    return redirect(url_for('team', team_id=team_id))
    #return redirect(url_for('show_teams'))


def connect_db():
    """Connects to the specified database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def init_db():
    """Initializees the database."""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


@app.cli.command('initdb')
def initdb_command():
    """Adds CLI command to initialize the database."""
    init_db()
    print('Initialized the database.')


def get_db():
    """Opens a new database connection if there is none yet for the current
    application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()