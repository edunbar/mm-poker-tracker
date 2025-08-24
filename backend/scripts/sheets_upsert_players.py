import os, json, logging
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from db.database import engine
from db.models import Player
from google.oauth2 import service_account
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO)

CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/backend/mm-poker-tracker-f0be11fedfdd.json")
SHEET_ID = os.getenv("NAME_VALIDATION_SHEET_ID", "18NVq3om_d5I-oGrwTT_f8BmyVFwz8Q3uFoPVNAFtxME")
RANGE = os.getenv("NAME_VALIDATION_RANGE", "Name Validation!A:B")

def sheets():
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build('sheets', 'v4', credentials=creds).spreadsheets()

def fetch_name_map() -> Dict[str, str]:
    resp = sheets().values().get(spreadsheetId=SHEET_ID, range=RANGE).execute()
    values: List[List[str]] = resp.get("values", [])
    # Expect rows: [display_name, external_id]
    return {r[1].strip(): r[0].strip() for r in values if len(r) >= 2 and r[1].strip()}

def run():
    id_to_name = fetch_name_map()
    inserted = updated = 0
    with Session(engine, future=True) as s:
        for ext_id, name in id_to_name.items():
            player = s.execute(select(Player).where(Player.external_id == ext_id)).scalar_one_or_none()
            if not player:
                # if someone already exists by same display_name, attach the ext_id
                player = s.execute(select(Player).where(func.lower(Player.display_name)==name.lower())).scalar_one_or_none()
                if not player:
                    s.add(Player(external_id=ext_id, display_name=name)); inserted += 1
                else:
                    player.external_id = ext_id
                    if player.display_name != name:
                        player.display_name = name
                    updated += 1
            else:
                if player.display_name != name:
                    player.display_name = name; updated += 1
        s.commit()
    logging.info(f"Done. inserted={inserted} updated={updated}")

if __name__ == "__main__":
    run()
