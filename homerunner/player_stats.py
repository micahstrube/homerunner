from urllib.request import urlopen
from bs4 import BeautifulSoup
import re
#import pyperclip

STATS_URL="https://www.fangraphs.com/leaders.aspx?pos=all&stats=bat&lg=all&qual=0&type=8&season=2018&month=0&season1=2018&ind=0&team=0&rost=0&age=0&filter=&players=0&page=1_2000"

def get_all_players_stats():
    players_home_runs = {}

    # Get FanGraphs page with player stats
    response = urlopen(STATS_URL)
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

'''
player_stats = get_all_players_stats()
output = ""
with open("players.txt", "r") as f:
    for player in f:
        player = player[:-1]
        if player in player_stats:
            print("%s: %s" % (player, player_stats[player]))
            output += "{player},{hr}\n".format(player=player, hr=player_stats[player])
        else:
            output += "{player},0\n".format(player=player)

pyperclip.copy(output)
'''
