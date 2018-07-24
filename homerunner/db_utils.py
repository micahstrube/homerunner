import flask
import sqlite3
from homerunner import app
import textwrap

def init_db():
    """Initializees the database."""
    db = get_db()
    cur = db.execute('select name from sqlite_master where type="table"')
    tables = cur.fetchall()
    table_names = []
    for table in tables:
        table_names.append(table['name'])

    # Create each table if it doesn't already exist
    if 'players' not in table_names:
        with app.open_resource('players.sql', mode='r') as f:
            db.cursor().executescript(f.read())
            app.logger.info('Created players table')
    else:
        app.logger.info('Players table already exists.')

    if 'teams' not in table_names:
        with app.open_resource('teams.sql', mode='r') as f:
            db.cursor().executescript(f.read())
            app.logger.info('Created teams table')
    else:
        app.logger.info('Teams table already exists.')

    if 'users' not in table_names:
        with app.open_resource('users.sql', mode='r') as f:
            db.cursor().executescript(f.read())
            app.logger.info('Created users table')
    else:
        app.logger.info('Users table already exists.')

    db.commit()


def get_db():
    """Opens a new database connection if there is none yet for the current
    application context.
    """
    if not hasattr(flask.g, 'sqlite_db'):
        flask.g.sqlite_db = connect_db()
    return flask.g.sqlite_db


def connect_db():
    """Connects to the specified database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(flask.g, 'sqlite_db'):
        flask.g.sqlite_db.close()


def user_exists(google_id):
    """
    Check if the specified google user exists in our database.

    :param google_id: User's google id
    :return: True if user exists in database, False if user does not exist.
    """
    db = get_db()
    cur = db.execute('select google_id from users where google_id = ?', [google_id])
    if cur.fetchone() is not None:
        return True
    return False


def create_user(google_id, google_email, name, picture_url, receive_notifications=True):
    """
    Check if specified google user exists in our database. If not, add them.

    :param google_id: User's google id
    :param google_email: User's google email address
    :param name: User's name
    :param receive_notifications: Whether the user opted in for email notifications.
    """
    if not user_exists(google_id):
        db = get_db()
        db.execute(textwrap.dedent("""\
            insert into users (google_id, email, name, picture_url, receive_email)
            values (?, ?, ?, ?, ?);
            """), [google_id, google_email, name, picture_url, receive_notifications])
    else:
        return None

