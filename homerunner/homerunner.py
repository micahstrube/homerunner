import os
import sqlite3
import textwrap
import google_auth_oauthlib.flow
import google.oauth2.credentials
from time import sleep
from player_stats import get_all_players_home_runs, update_player_database
import flask
#from flask import Flask, request, session, g, redirect, url_for, abort, \
#    render_template, flash

app = flask.Flask(__name__) # create the application instance

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

CLIENT_SECRETS_FILE = "client_secret.json"
OAUTH_SCOPES = ['openid', 'profile', 'email']

@app.route('/')
def show_dashboard():
    """Show dashboard of ranked teams and scores"""
    # If user not logged in, redirect to auth35ddd
    if 'credentials' not in flask.session:
        return flask.redirect('auth')

    # Load credentials from the session
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials']
    )

    # TODO: Get name from profile? Display user profile picture icon?

    # Save credentials back to session in case access token was refreshed.
    # TODO: In a production app, you likely want to save these
    #       credentials in a persistent database instead.
    flask.session['credentials'] = credentials_to_dict(credentials)

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

    return flask.render_template('dashboard.html', ranked_teams=ranked_teams)


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

    return flask.render_template('show_teams.html', players=players, teams=teams, team_scores=team_scores)


@app.route('/auth')
def auth():
    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=OAUTH_SCOPES)

    flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

    authorization_url, state = flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type='offline',
        # Enable incremental authorization. Recommended as a best practice.
        include_granted_scopes='true')

    # Store the state so the callback can verify the auth server response.
    flask.session['state'] = state

    return flask.redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response.
    state = flask.session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=OAUTH_SCOPES, state=state)
    flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = flask.request.url
    flow.fetch_token(authorization_response=authorization_response)

    # Store credentials in the session.
    # TODO: In a production app, you likely want to save these
    #       credentials in a persistent database instead.
    # TODO: Check database to see if user already exists, if not, add
    credentials = flow.credentials
    flask.session['credentials'] = credentials_to_dict(credentials)


    return flask.redirect(flask.url_for('show_teams'))


@app.route('/revoke')
def revoke():
  if 'credentials' not in flask.session:
    return ('You need to <a href="/authorize">authorize</a> before ' +
            'testing the code to revoke credentials.')

  credentials = google.oauth2.credentials.Credentials(
    **flask.session['credentials'])

  revoke = flask.requests.post('https://accounts.google.com/o/oauth2/revoke',
      params={'token': credentials.token},
      headers = {'content-type': 'application/x-www-form-urlencoded'})

  status_code = getattr(revoke, 'status_code')
  if status_code == 200:
    return('Credentials successfully revoked.')
  else:
    return('An error occurred.')


@app.route('/clear')
def clear_credentials():
  if 'credentials' in flask.session:
    del flask.session['credentials']
  return ('Credentials have been cleared.<br><br>')

def credentials_to_dict(credentials):
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login form"""
    error = None
    if flask.request.method == 'POST':
        if flask.request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif flask.request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            app.session['logged_in'] = True
            flask.flash('Logged in as {user}.'.format(user=flask.request.form['username']))
            return flask.redirect(flask.url_for('show_dashboard'))
    return flask.render_template('login.html', error=error)


@app.route('/logout')
def logout():
    """Logout, redirect to dashboard"""
    app.session.pop('logged_in', None)
    flask.flash('You have logged out')
    return flask.redirect(flask.url_for('show_dashboard'))


@app.route('/add_team', methods=['POST'])
def add_team():
    """Create new team"""
    db = get_db()
    db.execute('insert into teams (name) values (?)',
               [flask.equest.form['team_name']])
    db.commit()
    flask.flash('New team {team} successfully created'.format(team=flask.request.form['team_name']))
    return flask.redirect(flask.url_for('show_teams'))


@app.route('/team/<team_id>')
def team(team_id):
    """Page for team details and editing team"""
    db = get_db()
    cur = db.execute('select name, id from teams where id=?', [team_id])
    team = cur.fetchone()
    cur = db.execute('select name, id, home_runs from players where team_id=(?)', [team_id])
    players = cur.fetchall()
    return flask.render_template('team.html', team=team, players=players)


@app.route('/team/<team_id>/add_player', methods=['POST'])
def add_player_to_team(team_id):
    """Add player to specified team"""
    db = get_db()
    cur = db.execute('select id from players where name = ?',
                     [flask.request.form['player_name']])
    player = cur.fetchone()
    if player is not None:
        db.execute('update players set team_id = ? where id = ?',
                   [team_id, player['id']])
        db.commit()
    else:
        db.execute('insert into players (name, team_id) values (?, ?)',
                   [flask.request.form['player_name'], team_id])
        db.commit()
    flask.flash('{player} was successfully added to team {team}'
          .format(player=flask.request.form['player_name'], team=team_id))
    return flask.redirect(flask.url_for('team', team_id=team_id))


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


@app.cli.command('scraper')
def initscraper_cmmand():
    """Launches the scraper process to continually update the players
    home runs count
    """
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
    if not hasattr(flask.g, 'sqlite_db'):
        flask.g.sqlite_db = connect_db()
    return flask.g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(flask.g, 'sqlite_db'):
        flask.g.sqlite_db.close()


if __name__ == "__main__":
    app.run(ssl_context='adhoc')
