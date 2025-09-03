import requests
import logging
from sqlalchemy import select
from db.database import SessionLocal
from db.models import Player

def map_validated_names_to_players(player_data):
    """
    Fetches name-id mapping from players table and merges it with player data.
    Returns a list of player dicts with validated names.
    If any player ID does not map to a name, leaves validated_name blank.
    """
    logging.debug("Fetching name-id map from database and merging with player data")
    
    with SessionLocal() as db:
        # Fetch all players with external_id (verified players)
        players = db.execute(
            select(Player.external_id, Player.display_name)
            .where(Player.external_id.isnot(None))
        ).all()
        
        # Build mapping from external_id to display_name
        id_to_name = {}
        for external_id, display_name in players:
            if external_id and external_id.strip():
                id_to_name[external_id.strip()] = display_name.strip()
    
    logging.debug(f"Fetched name mappings: {id_to_name}")

    merged_players = []
    for player in player_data.get("playersInfos", []):
        player_id = player.get("id")
        validated_name = id_to_name.get(player_id, "")
        merged_player = player.copy()
        merged_player["validated_name"] = validated_name
        merged_players.append(merged_player)

    logging.debug(f"Merged player data: {merged_players}")
    return merged_players

def get_game_transactions(base_url):
    url = base_url + '/players_sessions'
    logging.debug(f"Constructed URL: {url}")
    try:
        response = requests.get(url)
        logging.debug(f"Raw response text: {response.text}")
    except Exception as e:
        logging.error(f"Exception during requests.get: {e}")
        raise Exception(f"Exception occurred: {str(e)}")

    if response.status_code != 200:
        logging.error("Failed to fetch data from the URL")
        raise Exception('Failed to fetch data from the URL')

    try:
        data = response.json()
        logging.debug(f"Parsed JSON data: {data}")
        if not isinstance(data, dict):
            logging.error(f"Expected dict from response.json(), got {type(data)}: {data}")
            raise Exception("Invalid response format from PokerNow API.")
    except Exception as e:
        logging.error(f"Exception during response.json(): {e}")
        raise Exception(f'Failed to parse JSON: {str(e)}')

    # Convert playersInfos dict to list
    players_infos_dict = data.get("playersInfos", {})
    if isinstance(players_infos_dict, dict):
        players_infos_list = list(players_infos_dict.values())
    else:
        players_infos_list = players_infos_dict  # Already a list or empty

    # Merge validated names
    merged_players = map_validated_names_to_players({"playersInfos": players_infos_list})
    data["playersInfos"] = merged_players
    return data