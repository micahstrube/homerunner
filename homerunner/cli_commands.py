from homerunner import app
from homerunner.player_stats import get_all_players_home_runs, update_player_database
from homerunner.db_utils import get_db, init_db
from time import sleep

@app.cli.command('scraper')
def scraper_command():
    scraper()


def scraper():
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
    app.logger.info('Database initialization complete.')

