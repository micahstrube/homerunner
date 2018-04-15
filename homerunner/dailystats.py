import json
from urllib.request import urlopen
from datetime import *

GAMEDAY_URL = "http://gd.mlb.com/components/game/mlb/year_{year}/month_{month}/day_{day}/master_scoreboard.json"

def todays_games():
    """Pull today's JSON from MLB GameDay"""
    now = datetime.now()
    month = now.month
    if month < 10:
        month = "0{month}".format(month=month)

    response = urlopen(GAMEDAY_URL.format(year=now.year, month=month, day=now.day))
    json_data = json.loads(response.read())

    # TODO: Check if days with single games have dict instead of list in JSON.
    todays_games = json_data['data']['games']['game']

    return todays_games


def todays_home_runs(todays_games: list):
    """Parse today's games and get number of home runs by player"""
    todays_home_runs = {} # { player_name: { 'home_runs': home_runs, 'game_id': game_id } }

    for game in todays_games:
        if ('home_runs' in game) and ('player' in game['home_runs']) and (game['status']['status'] in ['Final', 'Game Over']):
            # Stupid annoying case in MLB GameDay JSON where it only uses list format if there is > 1 player
            if isinstance(game['home_runs']['player'], list):
                for player in game['home_runs']['player']:
                    player_name = "{first} {last}".format(
                        first=player['first'], last=player['last'])
                    if player_name not in todays_home_runs:
                        todays_home_runs[player_name] = { 'home_runs': 1, 'game_id': game['id'] }
                    else:
                        new_home_runs = todays_home_runs[player_name]['home_runs'] + 1
                        todays_home_runs[player_name] = { 'home_runs': new_home_runs, 'game_id': game['id'] }
            elif isinstance(game['home_runs']['player'], dict):
                player_name = "{first} {last}".format(
                    first=game['home_runs']['player']['first'],
                    last=game['home_runs']['player']['last'])
                if player_name not in todays_home_runs:
                    todays_home_runs[player_name] = { 'home_runs': 1, 'game_id': game['id'] }
                else:
                    todays_home_runs[player_name] = { 'home_runs': new_home_runs, 'game_id': game['id'] }

    return todays_home_runs
