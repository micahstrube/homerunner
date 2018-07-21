import flask
app = flask.Flask(__name__)

import homerunner.views
import homerunner.cli_commands
import homerunner.db_utils
import os

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'homerunner.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default',
    STATS_SCRAPE_INTERVAL=60, # How often scrape requests are sent to 3rd party site
    CLIENT_SECRETS_FILE="client_secrts.json",
    OAUTH_SCOPES=['openid', 'profile', 'email']
    # to update players home runs
))
app.config.from_envvar('HOMERUNNER SETTINGS', silent=True)
