import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build

logging.basicConfig(level=logging.DEBUG)

CREDENTIALS_PATH = "/app/mm-poker-tracker-f0be11fedfdd.json"
NAME_VALIDATION_SHEET_ID = "18NVq3om_d5I-oGrwTT_f8BmyVFwz8Q3uFoPVNAFtxME"
NAME_VALIDATION_RANGE = "Name Validation!A:B"

def get_sheets_service():
    try:
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        service = build('sheets', 'v4', credentials=creds)
        return service.spreadsheets()
    except Exception as e:
        logging.error(f"Error initializing Google Sheets service: {e}")
        raise

def get_next_game_number():
    """
    Fetches the most recent game number from 'Game Ledger1' column A and returns the next game number.
    """
    GAME_LEDGER_SHEET_ID = "18NVq3om_d5I-oGrwTT_f8BmyVFwz8Q3uFoPVNAFtxME"
    GAME_LEDGER_RANGE = "Game Ledger1!A:A"
    sheet = get_sheets_service()
    try:
        result = sheet.values().get(
            spreadsheetId=GAME_LEDGER_SHEET_ID,
            range=GAME_LEDGER_RANGE
        ).execute()
        values = result.get("values", [])
        # Flatten and filter out non-integer values
        numbers = []
        for row in values:
            if row and row[0].isdigit():
                numbers.append(int(row[0]))
        if numbers:
            next_game_number = max(numbers) + 1
        else:
            next_game_number = 1
        logging.debug(f"Next game number: {next_game_number}")
        return next_game_number
    except Exception as e:
        logging.error(f"Error fetching game number: {e}")
        raise

def map_validated_names_to_players(player_data):
    """
    Fetches name-id mapping from Google Sheets and merges it with player data.
    Returns a list of player dicts with validated names.
    If any player ID does not map to a name, leaves validated_name blank.
    """
    logging.debug("Fetching name-id map and merging with player data")
    sheet = get_sheets_service()
    try:
        result = sheet.values().get(
            spreadsheetId=NAME_VALIDATION_SHEET_ID,
            range=NAME_VALIDATION_RANGE
        ).execute()
        values = result.get("values", [])
        logging.debug(f"Fetched values: {values}")
        id_to_name = {row[1]: row[0] for row in values if len(row) >= 2}
    except Exception as e:
        logging.error(f"Error fetching name-id map: {e}")
        raise

    merged_players = []
    for player in player_data.get("playersInfos", []):
        player_id = player.get("id")
        validated_name = id_to_name.get(player_id, "")
        merged_player = player.copy()
        merged_player["validated_name"] = validated_name
        merged_players.append(merged_player)

    logging.debug(f"Merged player data: {merged_players}")
    return merged_players

def upload_game_to_sheets(game_data):
    SHEET_ID = "18NVq3om_d5I-oGrwTT_f8BmyVFwz8Q3uFoPVNAFtxME"
    RANGE_NAME = "Game Ledger1!A1"

    logging.debug("Starting upload_game_to_sheets function")
    logging.debug(f"Using credentials file at: {CREDENTIALS_PATH}")

    sheet = get_sheets_service()

    from datetime import datetime
    raw_date = game_data.get("date")
    if raw_date:
        try:
            parsed_date = datetime.fromisoformat(raw_date)
        except ValueError:
            try:
                parsed_date = datetime.strptime(raw_date, "%m/%d/%Y")
            except ValueError:
                parsed_date = datetime.today()
    else:
        parsed_date = datetime.today()
    game_date = parsed_date.strftime("%-m/%-d/%Y")  # e.g., 8/20/2025

    next_game_number = get_next_game_number()

    # Check for missing validated names
    missing_ids = [
        player.get("id", "")
        for player in game_data.get("playersInfos", [])
        if not player.get("validated_name")
    ]
    if missing_ids:
        error_msg = (
            "The following IDs do not have a validated name attached: "
            + ", ".join(missing_ids)
        )
        logging.error(error_msg)
        raise ValueError(error_msg)

    values = [
        [
            next_game_number,                              # game number
            player.get("validated_name", ""),              # Name (from mapping)
            round(player.get("buyInSum", 0) / 100, 2),     # buy in (dollars)
            round((player.get("buyOutSum", 0) + player.get("inGame", 0)) / 100, 2),    # cash out (dollars)
            game_date                                      # date
        ]
        for player in game_data.get("playersInfos", [])
    ]
    body = {"values": values}
    logging.debug(f"Prepared values for upload: {values}")

    try:
        result = sheet.values().append(
            spreadsheetId=SHEET_ID,
            range=RANGE_NAME,
            valueInputOption="RAW",
            body=body
        ).execute()
        logging.debug(f"Google Sheets append result: {result}")
    except Exception as e:
        logging.error(f"Error appending values to Google Sheets: {e}")
        raise

    return {
        "status": "success",
        "updatedRange": result.get("updates", {}).get("updatedRange")
    }