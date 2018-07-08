import os
import sqlite3
import textwrap
from time import sleep
from .player_stats import get_all_players_home_runs, update_player_database

from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash

app = Flask(__name__) # create the application instance

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'homerunner.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default',
    STATS_SCRAPE_INTERVAL=60, # How often scrape requests are sent to 3rd party site
                              # to update players home runs
))
app.config.from_envvar('HOMERUNNER SETTINGS', silent=True)


@app.route('/')
def show_dashboard():
    """Show dashboard of ranked teams and scores"""
    db = get_db()
    cur = db.execute('select id from teams')
    ranked_teams = cur.fetchall()
    for team in ranked_teams:
        cur = db.execute('select SUM(home_runs) from players where team_id = ?', [team['id']])
        score = cur.fetchone()[0]
        print("Score: {score}".format(score=score))
        db.execute('update teams set score = ? where id = ?', [score, team['id']])
        db.commit()

    cur = db.execute('select name, id, score from teams order by score desc')
    ranked_teams = cur.fetchall()

    return render_template('dashboard.html', ranked_teams=ranked_teams)


@app.route('/teams')
def show_teams():
    """Show menu of teams and players on teams"""
    db = get_db()
    cur = db.execute(textwrap.dedent("""\
      select name, team_id, home_runs from players 
      where team_id is not null
      """))
    players = cur.fetchall()
    cur = db.execute('select name, id from teams order by name')
    teams = cur.fetchall()
    cur = db.execute(textwrap.dedent("""\
      select teams.id as id,
      teams.name as name,
      SUM(players.home_runs) as score
      from teams inner join players on teams.id=players.team_id
      group by teams.id
      """))
    team_scores = cur.fetchall()

    return render_template('show_teams.html', players=players, teams=teams, team_scores=team_scores)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login form"""
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('Logged in as {user}.'.format(user=request.form['username']))
            return redirect(url_for('show_dashboard'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    """Logout, redirect to dashboard"""
    session.pop('logged_in', None)
    flash('You have logged out')
    return redirect(url_for('show_dashboard'))


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
    cur = db.execute('select name, id, home_runs from players where team_id=(?)', [team_id])
    players = cur.fetchall()
    return render_template('team.html', team=team, players=players)


@app.route('/team/<team_id>/add_player', methods=['POST'])
def add_player_to_team(team_id):
    """Add player to specified team"""
    db = get_db()
    cur = db.execute('select id from players where name = ?',
                     [request.form['player_name']])
    player = cur.fetchone()
    if player is not None:
        db.execute('update players set team_id = ? where id = ?',
                   [team_id, player['id']])
        db.commit()
    else:
        db.execute('insert into players (name, team_id) values (?, ?)',
                   [request.form['player_name'], team_id])
        db.commit()
    flash('{player} was successfully added to team {team}'
          .format(player=request.form['player_name'], team=team_id))
    return redirect(url_for('team', team_id=team_id))


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


@app.cli.command('initscraper')
def initscraper_cmmand():
    """Launches the scraper process to continually update the players
    home runs count"""
    app.logger.info('Starting stats scraper.')
    scrape_interval = app.config['STATS_SCRAPE_INTERVAL']
    app.logger.debug('STATS_SCRAPE_INTERVAL=%s' % scrape_interval)
    db = get_db()
    while True:
        update_player_database(db, get_all_players_home_runs())
        app.logger.info('Retrieved latest player stats and updated database.')
        sleep(scrape_interval)


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