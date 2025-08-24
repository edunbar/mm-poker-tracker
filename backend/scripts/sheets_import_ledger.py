# backend/scripts/sheets_import_ledger.py
import os
import logging
import datetime as dt
from decimal import Decimal
from typing import List, Optional, Union
import argparse

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from db.database import engine
from db.models import (
    Game,
    Player,
    GamePlayer,
    Session as SessionModel,
    SessionPlayerSummary,
)

from google.oauth2 import service_account
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO)

# --- Config via env (override in docker exec with -e ...) ---
CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/app/mm-poker-tracker-f0be11fedfdd.json")
LEDGER_SHEET_ID = os.getenv("GAME_LEDGER_SHEET_ID", "18NVq3om_d5I-oGrwTT_f8BmyVFwz8Q3uFoPVNAFtxME")
LEDGER_RANGE = os.getenv("GAME_LEDGER_RANGE", "Game Ledger1!A:E")  # A: Game #, B: Player, C: Buy-In, D: Cash Out, E: Date
PUBLIC_CODE = os.getenv("TARGET_GAME_PUBLIC_CODE")  # required

# ---------------- Google Sheets helpers ----------------
def sheets():
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return build("sheets", "v4", credentials=creds).spreadsheets()

def fetch_ledger_df() -> pd.DataFrame:
    resp = sheets().values().get(spreadsheetId=LEDGER_SHEET_ID, range=LEDGER_RANGE).execute()
    values: List[List[str]] = resp.get("values", [])
    if not values:
        return pd.DataFrame(columns=["Game #", "Player", "Buy-In", "Cash Out", "Date"])

    header, rows = values[0], values[1:]
    rename = {}
    for h in header:
        key = h.strip().lower()
        if key in {"game #", "game", "game number"}:
            rename[h] = "Game #"
        elif key in {"player", "name"}:
            rename[h] = "Player"
        elif key in {"buy-in", "buy in", "buyin"}:
            rename[h] = "Buy-In"
        elif key in {"cash out", "cash-out", "cashout"}:
            rename[h] = "Cash Out"
        elif key in {"date", "session date"}:
            rename[h] = "Date"

    df = pd.DataFrame(rows, columns=header).rename(columns=rename)

    # Coerce numeric columns
    for col in ["Buy-In", "Cash Out"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Keep a string copy for grouping (even when Date is blank)
    if "Date" not in df.columns:
        df["Date"] = ""
    df["Date_str"] = df["Date"].astype(str)
    return df

# ---------------- Parsing helpers ----------------
def money_to_cents(v) -> int:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return 0
    return int((Decimal(str(v)).quantize(Decimal("0.01")) * 100))

def _excel_serial_to_date(n: Union[int, float]) -> Optional[dt.datetime]:
    """Convert Excel serial date to datetime (UTC-naive)."""
    try:
        n = float(n)
    except Exception:
        return None
    try:
        ts = pd.to_datetime(n, unit="D", origin="1899-12-30")
        if pd.isna(ts):
            return None
        # return naive datetime (no tzinfo) for consistency with DB defaults
        return dt.datetime.fromtimestamp(ts.timestamp()).replace(tzinfo=None)
    except Exception:
        return None

def parse_date_any(v: object) -> Optional[dt.datetime]:
    """Parse strings like '8/11/2025', '2025-08-11', excel serials, or datetime/date."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, dt.datetime):
        return v
    if isinstance(v, dt.date):
        return dt.datetime.combine(v, dt.time.min)

    s = str(v).strip()
    if not s or s.lower() in {"none", "nan", "nat"}:
        return None

    # Fast path: known common formats
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return dt.datetime.strptime(s, fmt)
        except Exception:
            pass

    # Pandas parser (handles many variants)
    try:
        ts = pd.to_datetime(s, errors="coerce")
        if not pd.isna(ts):
            return dt.datetime.fromtimestamp(ts.timestamp()).replace(tzinfo=None)
    except Exception:
        pass

    # Try as excel serial number (string)
    excel_attempt = _excel_serial_to_date(s)
    if excel_attempt:
        return excel_attempt

    return None

def format_session_ext_id(prefix: str, game_no: str, dt_obj: Optional[dt.datetime]) -> str:
    if dt_obj:
        return f"{prefix}-{(game_no or 'unknown').strip()}-{dt_obj.date().isoformat()}"
    # mark as nodate but remain deterministic
    sanitized = (game_no or "unknown").strip().replace(" ", "")
    return f"{prefix}-{sanitized}-nodate"

# ---------------- Main importer ----------------
def run():
    parser = argparse.ArgumentParser(description="Import Game Ledger sheet to sessions & summaries.")
    parser.add_argument("--fallback-date", help="YYYY-MM-DD to use when a row's Date is missing")
    args = parser.parse_args()

    fallback_env = os.getenv("FALLBACK_LEDGER_DATE")
    fallback_date = args.fallback_date or fallback_env
    fallback_dt = None
    if fallback_date:
        try:
            fallback_dt = dt.datetime.strptime(fallback_date, "%Y-%m-%d")
        except Exception:
            raise ValueError(f"Invalid --fallback-date / FALLBACK_LEDGER_DATE: {fallback_date} (expected YYYY-MM-DD)")

    if not PUBLIC_CODE:
        raise RuntimeError("Set TARGET_GAME_PUBLIC_CODE env var to your game's public_code.")

    df = fetch_ledger_df()
    expected = {"Game #", "Player", "Buy-In", "Cash Out", "Date"}
    if not expected.issubset(set(df.columns)):
        raise ValueError(f"Ledger missing columns. Have {list(df.columns)}, need {sorted(expected)}")

    # Group by (Game #, Date_str) so blanks don't crash
    df["_group"] = df["Game #"].astype(str).str.strip() + "|" + df["Date_str"].str.strip()

    missing_dates_groups = 0

    with Session(engine, future=True) as s:
        # Find target game
        game = s.execute(select(Game).where(Game.public_code == PUBLIC_CODE)).scalar_one_or_none()
        if not game:
            raise ValueError(f"Game with public_code={PUBLIC_CODE!r} not found")

        for gkey, grp in df.groupby("_group"):
            game_no = str(grp.iloc[0]["Game #"]).strip()
            parsed = parse_date_any(grp.iloc[0]["Date"])
            if not parsed:
                missing_dates_groups += 1
                parsed = fallback_dt or dt.datetime.utcnow()

            ext_id = format_session_ext_id("ledger", game_no, parsed)

            # Upsert session by (game_id, external_id)
            sess = s.execute(
                select(SessionModel).where(
                    SessionModel.game_id == game.id,
                    SessionModel.external_id == ext_id,
                )
            ).scalar_one_or_none()
            if not sess:
                sess = SessionModel(
                    game_id=game.id,
                    external_id=ext_id,
                    started_at=parsed,
                    ended_at=None,
                    end_session_json=None,
                )
                s.add(sess)
                s.flush()

            # Upsert player summaries
            for _, row in grp.iterrows():
                name = str(row["Player"]).strip()
                buy_in = money_to_cents(row["Buy-In"])
                cash_out = money_to_cents(row["Cash Out"])
                in_game = 0
                net = cash_out - buy_in

                player = s.execute(
                    select(Player).where(func.lower(Player.display_name) == name.lower())
                ).scalar_one_or_none()
                if not player:
                    player = Player(display_name=name)
                    s.add(player)
                    s.flush()

                link = s.execute(
                    select(GamePlayer).where(
                        GamePlayer.game_id == game.id,
                        GamePlayer.player_id == player.id,
                    )
                ).scalar_one_or_none()
                if not link:
                    s.add(GamePlayer(game_id=game.id, player_id=player.id))

                sps = s.execute(
                    select(SessionPlayerSummary).where(
                        SessionPlayerSummary.session_id == sess.id,
                        SessionPlayerSummary.player_id == player.id,
                    )
                ).scalar_one_or_none()
                if not sps:
                    s.add(
                        SessionPlayerSummary(
                            session_id=sess.id,
                            player_id=player.id,
                            buy_in_sum=buy_in,
                            cash_out_sum=cash_out,
                            in_game=in_game,
                            net=net,
                            names=[name],
                        )
                    )
                else:
                    sps.buy_in_sum = buy_in
                    sps.cash_out_sum = cash_out
                    sps.in_game = in_game
                    sps.net = net
                    sps.names = [name]

        s.commit()

    if missing_dates_groups:
        logging.warning(
            f"Imported with {missing_dates_groups} group(s) missing Date; "
            f"used fallback ({fallback_dt.date() if fallback_dt else 'today UTC'})."
        )
    logging.info("Ledger import complete.")

if __name__ == "__main__":
    run()
