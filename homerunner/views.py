import flask
import textwrap
import google_auth_oauthlib.flow
import google.oauth2.credentials
import requests
from homerunner import app
from homerunner.db_utils import get_db, user_exists, create_user
from homerunner.auth import get_user_google_account_info, credentials_to_dict
#from flask import Flask, request, session, g, redirect, url_for, abort, \
#    render_template, flash

@app.route('/')
def show_dashboard():
    """Show dashboard of ranked teams and scores"""
    # If user not logged in, redirect to auth35ddd
    if 'credentials' not in flask.session:
        return flask.redirect('auth')
    flask.session['logged_in'] = True
    # Refresh credentials from the session.
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])

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

    return flask.render_template('dashboard.html',
                                 ranked_teams=ranked_teams,
                                 picture_url=flask.session['picture_url'])


@app.route('/teams')
def show_teams():
    """Show menu of teams and players on teams"""
    if 'credentials' not in flask.session:
        return flask.redirect('auth')
    flask.session['logged_in'] = True
    # Refresh credentials from the session.
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])

    picture_url = flask.session['picture_url']

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

    return flask.render_template('show_teams.html',
                                 picture_url=picture_url,
                                 players=players,
                                 teams=teams,
                                 team_scores=team_scores)


@app.route('/auth')
def auth():
    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        app.config['CLIENT_SECRETS_FILE'],
        scopes=app.config['OAUTH_SCOPES'])

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
        app.config['CLIENT_SECRETS_FILE'],
        scopes=app.config['OAUTH_SCOPES'])
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

    # Get user's google account info and add it to session
    google_id, email, name, picture_url = get_user_google_account_info()
    flask.session.update(google_id=google_id,
                         email=email,
                         name=name,
                         picture_url=picture_url)
    # If user does not exist in our database, add them
    if not user_exists(google_id):
        # TODO: Future code to redirect to signup page?
        create_user(google_id=google_id,
                    google_email=email,
                    name=name,
                    picture_url=picture_url,
                    receive_notifications=True)

    return flask.redirect(flask.url_for('show_teams'))


@app.route('/revoke')
def revoke():
    if 'credentials' not in flask.session:
        return ('You need to <a href="/authorize">authorize</a> before ' +
                'testing the code to revoke credentials.')

    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])

    revoke = requests.post('https://accounts.google.com/o/oauth2/revoke',
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
               [flask.request.form['team_name']])
    db.commit()
    flask.flash('New team {team} successfully created'.format(team=flask.request.form['team_name']))
    return flask.redirect(flask.url_for('show_teams'))


@app.route('/team/<team_id>')
def team(team_id):
    """Page for team details and editing team"""
    if 'credentials' not in flask.session:
        return flask.redirect('auth')
    flask.session['logged_in'] = True
    # Refresh credentials from the session.
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])
    db = get_db()
    cur = db.execute('select name, id from teams where id=?', [team_id])
    team = cur.fetchone()
    cur = db.execute('select name, id, home_runs from players where team_id=(?)', [team_id])
    players = cur.fetchall()
    return flask.render_template('team.html',
                                 picture_url=flask.session['picture_url'],
                                 team=team,
                                 players=players)


@app.route('/team/<team_id>/add_player', methods=['POST'])
def add_player_to_team(team_id):
    """Add player to specified team"""
    flask.session['logged_in'] = True
    # Refresh credentials from the session.
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])

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
    return flask.redirect(flask.url_for('team',
                                        picture_url=flask.session['picture_url'],
                                        team_id=team_id))


