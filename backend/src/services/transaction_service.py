import requests
import logging

def get_game_transactions(base_url):
    url = base_url + '/players_sessions'
    logging.debug(f"Constructed URL: {url}")
    try:
        response = requests.get(url)
    except Exception as e:
        logging.error(f"Exception during requests.get: {e}")
        raise Exception(f"Exception occurred: {str(e)}")

    if response.status_code != 200:
        logging.error("Failed to fetch data from the URL")
        raise Exception('Failed to fetch data from the URL')

    try:
        data = response.json()
    except Exception as e:
        logging.error(f"Exception during response.json(): {e}")
        raise Exception(f'Failed to parse JSON: {str(e)}')

    return data