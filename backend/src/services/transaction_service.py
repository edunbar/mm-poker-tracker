import cloudscraper
import logging
from sqlalchemy import select
from db.database import SessionLocal
from db.models import Player

def create_browser_scraper():
    """
    Create a cloudscraper instance with browser-like headers to bypass Cloudflare.
    """
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    # Add additional browser-like headers
    scraper.headers.update({
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    })

    return scraper

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

def fetch_ledger_csv(base_url):
    """
    Attempt to fetch the ledger CSV from PokerNow.
    Returns dict with success status, content, and optional error message.
    """
    try:
        game_id = base_url.rstrip('/').split('/')[-1]
        ledger_url = f"https://www.pokernow.club/games/{game_id}/ledger_{game_id}.csv"
        logging.debug(f"Attempting to fetch ledger CSV from: {ledger_url}")

        scraper = create_browser_scraper()
        response = scraper.get(ledger_url, timeout=10)

        if response.status_code == 200:
            csv_content = response.text
            logging.info(f"Successfully fetched ledger CSV ({len(csv_content)} bytes)")
            return {
                "success": True,
                "url": ledger_url,
                "size_bytes": len(csv_content),
                "content": csv_content
            }
        else:
            logging.warning(f"Failed to fetch ledger CSV: HTTP {response.status_code}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "url": ledger_url,
                "content": None
            }
    except Exception as e:
        logging.error(f"Exception fetching ledger CSV: {e}")
        return {
            "success": False,
            "error": str(e),
            "content": None
        }

def get_game_transactions(base_url):
    url = base_url + '/players_sessions'
    logging.debug(f"Constructed URL: {url}")
    try:
        scraper = create_browser_scraper()
        # Ensure automatic decompression by accessing .text (not .content)
        response = scraper.get(url, timeout=15)
        logging.debug(f"Response status code: {response.status_code}")
        logging.debug(f"Response headers: {dict(response.headers)}")

        # Force text decoding to handle gzip
        response_text = response.text
        logging.debug(f"Successfully fetched data from PokerNow (length: {len(response_text)})")
        logging.debug(f"Response text preview: {response_text[:200] if response_text else 'EMPTY'}")
    except Exception as e:
        logging.error(f"Exception during cloudscraper.get: {e}")
        raise Exception(f"Exception occurred: {str(e)}")

    if response.status_code != 200:
        logging.error("Failed to fetch data from the URL")
        raise Exception('Failed to fetch data from the URL')

    try:
        # Use response.json() which handles encoding automatically
        data = response.json()
        logging.debug(f"Parsed JSON data keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        if not isinstance(data, dict):
            logging.error(f"Expected dict from response.json(), got {type(data)}: {data}")
            raise Exception("Invalid response format from PokerNow API.")
    except ValueError as e:
        logging.error(f"JSON parsing error: {e}")
        logging.error(f"Response text was: {response_text[:500]}")
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

    ledger_status = fetch_ledger_csv(base_url)
    data["ledger_csv"] = ledger_status

    return data