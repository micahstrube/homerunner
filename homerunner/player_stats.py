import re
import flask
from homerunner import app, db_utils
from urllib.request import urlopen
from bs4 import BeautifulSoup

app.config['STATS_URL'] = "https://www.fangraphs.com/leaders.aspx?pos=all&stats=bat&lg=all&qual=0&type=8&season=2018&month=0&season1=2018&ind=0&team=0&rost=0&age=0&filter=&players=0&page=1_2000"

def get_all_players_home_runs():
    """Scrape current home runs count for all player from STATS_URL"""
    stats_url = app.config['STATS_URL']
    players_home_runs = {}

    # Get FanGraphs page with player stats
    app.logger.info('Retrieving stats from STATS_URL')
    response = urlopen(stats_url)
    # Create html parser and grab all the players stats rows
    # Each <tr> has an id of "LeaderBoard1_dg1_ct100__###" where ### is a 3 digit number for the row number
    soup = BeautifulSoup(response, 'html.parser')
    stats_table = soup.find_all(id=re.compile("^LeaderBoard1_dg1_ctl00__"))
    # Grab the player names and home run count from the table
    for row in stats_table:
        columns = list(row.children)
        player_name = list(list(columns[2].children)[0].children)[0]
        player_home_runs = list(columns[6].children)[0]
        # Add this player to the dict
        players_home_runs[player_name] = player_home_runs
    return players_home_runs

def update_player_database(db, players_stats):
    """Update database with latest player home runs"""
    for player in players_stats:
        cur = db.execute('select home_runs, id from players where name=?', [player])
        db_player = cur.fetchone()
        # If player found, update, otherwise insert
        if db_player == None:
            db.execute('insert into players (name, home_runs) values (?, ?)',
                       [player, players_stats[player]])
        else:
            db.execute('update players set home_runs = ? where name = ?',
                       [players_stats[player], player])
        db.commit()

