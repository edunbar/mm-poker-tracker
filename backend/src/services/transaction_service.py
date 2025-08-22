import requests
import logging
from services.sheets_service import map_validated_names_to_players

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