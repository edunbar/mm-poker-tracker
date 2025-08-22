import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build

logging.basicConfig(level=logging.DEBUG)

def upload_game_to_sheets(data):
    SHEET_ID = "1OlEoYPHOsPAmuWRtxacPCEVpT9XhyOvivv1R6FbHJAQ"
    RANGE_NAME = "Sheet10!A1" 

    logging.debug("Starting upload_game_to_sheets function")
    credentials_path = "/app/mm-poker-tracker-0392299a602a.json"
    logging.debug(f"Using credentials file at: {credentials_path}")

    try:
        creds = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        logging.debug("Loaded Google service account credentials successfully")
    except Exception as e:
        logging.error(f"Error loading credentials file: {e}")
        raise

    try:
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        logging.debug("Google Sheets service built successfully")
    except Exception as e:
        logging.error(f"Error building Google Sheets service: {e}")
        raise

    values = [
        [
            ", ".join(player.get("names", [])),  # names as comma-separated string
            player.get("buyInSum"),
            player.get("buyOutSum"),
            player.get("inGame"),
            player.get("net"),
            player.get("id"),
        ]
        for player in data.get("playersInfos", [])
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