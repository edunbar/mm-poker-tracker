# services/dual_write_service.py
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import (
    Game, Player, GamePlayer,
    Session as SessionModel,
    SessionPlayerSummary,
    AuditLog,
)

# Reuse your Sheets helpers (or keep them here if you prefer)
from services.sheets_service import get_sheets_service

# ---- Config for your Google Sheet tabs/ranges ----
GAME_LEDGER_SHEET_ID = "18NVq3om_d5I-oGrwTT_f8BmyVFwz8Q3uFoPVNAFtxME"
GAME_LEDGER_RANGE = "Game Ledger1!A1"
NAME_VALIDATION_SHEET_ID = "18NVq3om_d5I-oGrwTT_f8BmyVFwz8Q3uFoPVNAFtxME"
NAME_VALIDATION_RANGE = "Name Validation!A:B"

log = logging.getLogger(__name__)


# ---------- helpers ----------
def _players_dict_to_list(players_infos: Any) -> List[Dict[str, Any]]:
    """Accept dict keyed by player id or a list. Return list of player dicts with 'id' present."""
    if isinstance(players_infos, dict):
        out: List[Dict[str, Any]] = []
        for pid, info in players_infos.items():
            item = dict(info) if isinstance(info, dict) else {"id": pid}
            item.setdefault("id", pid)
            out.append(item)
        return out
    return list(players_infos or [])


def _chips_to_dollars(chips: int) -> float:
    """Sheets expects dollars; your incoming numbers are 'chips' that equal cents in dollars."""
    if chips is None:
        return 0.0
    return round(chips / 100.0, 2)


def _format_mmddyyyy(dt_obj: datetime) -> str:
    # Using Linux-style %-m/%-d; if you run into portability issues on Windows, change to %#m/%#d
    return dt_obj.strftime("%-m/%-d/%Y")


def _today_naive_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------- core steps ----------
def _fetch_name_map() -> Dict[str, str]:
    """
    Read "Name Validation!A:B" as [display_name, external_id] rows and build {external_id: display_name}.
    """
    sheet = get_sheets_service()
    res = sheet.values().get(spreadsheetId=NAME_VALIDATION_SHEET_ID, range=NAME_VALIDATION_RANGE).execute()
    values = res.get("values", [])
    id_to_name: Dict[str, str] = {}
    for row in values:
        if len(row) >= 2:
            name = (row[0] or "").strip()
            pid = (row[1] or "").strip()
            if pid:
                id_to_name[pid] = name
    return id_to_name


def _compute_next_game_number() -> int:
    """Peek at Game Ledger column A and return max + 1, or 1 if empty."""
    sheet = get_sheets_service()
    res = sheet.values().get(spreadsheetId=GAME_LEDGER_SHEET_ID, range="Game Ledger1!A:A").execute()
    values = res.get("values", [])
    nums: List[int] = []
    for row in values:
        if row and str(row[0]).isdigit():
            nums.append(int(row[0]))
    return (max(nums) + 1) if nums else 1


def _append_ledger_rows(game_number: int, date_for_sheet: str, validated_players: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Append rows to Game Ledger:
    [game_number, validated_name, buy-in $ , cash-out $ , date M/D/YYYY]
    """
    sheet = get_sheets_service()
    rows = []
    for p in validated_players:
        buy_in = int(p.get("buyInSum") or 0)       # chips
        cash_out = int(p.get("buyOutSum") or 0)    # chips
        in_game = int(p.get("inGame") or 0)        # chips
        rows.append([
            game_number,
            p.get("validated_name", ""),
            _chips_to_dollars(buy_in),
            _chips_to_dollars(cash_out + in_game),
            date_for_sheet,
        ])
    body = {"values": rows}
    return sheet.values().append(
        spreadsheetId=GAME_LEDGER_SHEET_ID,
        range=GAME_LEDGER_RANGE,
        valueInputOption="RAW",
        body=body
    ).execute()


def _require_admin_for_game(db: Session, public_code: str, admin_code: str) -> Game:
    game = db.execute(select(Game).where(Game.public_code == public_code)).scalar_one_or_none()
    if not game:
        raise ValueError("Game not found")
    if game.admin_code != admin_code:
        raise PermissionError("Invalid admin code")
    return game


def _upsert_db_for_session(
    db: Session,
    game: Game,
    session_external_id: str,
    when: datetime,
    payload_json: Dict[str, Any],
    validated_players: List[Dict[str, Any]],
    game_number_for_meta: int,
) -> Tuple[str, int]:
    """
    Upsert session + summaries + players + links. Returns (session_id, affected_rows).
    """
    # Session (unique by game_id + external_id)
    sess = db.execute(
        select(SessionModel).where(
            SessionModel.game_id == game.id,
            SessionModel.external_id == session_external_id
        )
    ).scalar_one_or_none()
    if not sess:
        sess = SessionModel(
            game_id=game.id,
            external_id=session_external_id,
            started_at=when,
            end_session_json=payload_json,   # keep raw snapshot
        )
        db.add(sess)
        db.flush()
    else:
        # Update fields (keep last payload)
        sess.started_at = sess.started_at or when
        sess.end_session_json = payload_json

    # Optional: store ledger game number in session JSON meta if you later add a meta column; for now store into end_session_json
    try:
        j = dict(sess.end_session_json or {})
        j.setdefault("meta", {})["ledger_game_number"] = game_number_for_meta
        sess.end_session_json = j
    except Exception:
        # ignore if JSONB merge fails for some reason
        pass

    # Summaries
    affected = 0
    for p in validated_players:
        ext_pid = (p.get("id") or "").strip() or None
        names = p.get("names") or []
        display_name = (p.get("validated_name") or (names[0] if names else "Unknown")).strip()

        # Find player: prefer external_id; else by display_name
        player = None
        if ext_pid:
            player = db.execute(select(Player).where(Player.external_id == ext_pid)).scalar_one_or_none()
        if not player:
            player = db.execute(select(Player).where(func.lower(Player.display_name) == display_name.lower())).scalar_one_or_none()
        if not player:
            player = Player(external_id=ext_pid, display_name=display_name)
            db.add(player)
            db.flush()
        else:
            # Attach external_id later if missing (#10)
            if ext_pid and not player.external_id:
                player.external_id = ext_pid
            # If display name changed to the validated name, update it
            if display_name and player.display_name != display_name:
                player.display_name = display_name

        # Link to game
        link = db.execute(
            select(GamePlayer).where(GamePlayer.game_id == game.id, GamePlayer.player_id == player.id)
        ).scalar_one_or_none()
        if not link:
            db.add(GamePlayer(game_id=game.id, player_id=player.id))

        # Upsert summary
        buy_in = int(p.get("buyInSum") or 0)
        cash_out = int(p.get("buyOutSum") or 0)
        in_game = int(p.get("inGame") or 0)
        net = int(p.get("net") or (cash_out + in_game - buy_in))

        sps = db.execute(
            select(SessionPlayerSummary).where(
                SessionPlayerSummary.session_id == sess.id,
                SessionPlayerSummary.player_id == player.id
            )
        ).scalar_one_or_none()
        if not sps:
            db.add(SessionPlayerSummary(
                session_id=sess.id,
                player_id=player.id,
                buy_in_sum=buy_in,       # chips in DB
                cash_out_sum=cash_out,
                in_game=in_game,
                net=net,
                names=names or [display_name],
            ))
        else:
            sps.buy_in_sum = buy_in
            sps.cash_out_sum = cash_out
            sps.in_game = in_game
            sps.net = net
            sps.names = names or [display_name]
        affected += 1

    return str(sess.id), affected


def _write_audit(
    db: Session,
    game: Game,
    session_id: str,
    admin_code: str,
    action: str,
    target: str,
    payload_before: Any,
    payload_after: Any,
):
    db.add(AuditLog(
        game_id=game.id,
        session_id=session_id,
        actor_kind="admin_code",
        actor_id=admin_code[:8] + "…" if admin_code else None,
        action=action,
        target_table=target,
        target_id=session_id,
        before=payload_before,
        after=payload_after,
    ))


# ---------- public API ----------
def upload_game_dual_write(
    *,
    public_code: str,
    admin_code: str,
    session_id: str,            # PokerNow sessionId (required)
    game_data: Dict[str, Any],  # payload with playersInfos as dict
    date_iso: str | None = None # optional ISO date, uses today if None
) -> Dict[str, Any]:
    """
    End-to-end:
      1) Validate admin for game
      2) Validate all players have mapping in Name Validation sheet (hard fail on any missing)  (#9)
      3) Begin DB txn and upsert everything
      4) Compute next game number and append to ledger (Sheets is source for that)
      5) If Sheets append fails, rollback DB and raise
      6) Commit DB; write audit; return result
    """
    # ----- Step 0: normalize inputs -----
    players = _players_dict_to_list(game_data.get("playersInfos", {}))
    if not players:
        raise ValueError("No players found in payload")

    # Validate names via sheet, but allow validated_name from payload
    id_to_name = _fetch_name_map()
    missing = [
        p.get("id", "")
        for p in players
        if not (id_to_name.get(p.get("id", "")) or p.get("validated_name"))
    ]
    if missing:
        raise ValueError("Missing validated names for player IDs: " + ", ".join(missing))

    # Attach validated_name into working copy, prefer payload value if present
    validated_players: List[Dict[str, Any]] = []
    for p in players:
        pid = p.get("id")
        vp = dict(p)
        vp["validated_name"] = p.get("validated_name") or id_to_name.get(pid, "")
        validated_players.append(vp)

    # Decide session timestamp for DB
    when = None
    if date_iso:
        try:
            when = datetime.fromisoformat(date_iso)
        except Exception:
            when = _today_naive_utc()
    else:
        when = _today_naive_utc()

    # For Sheets date formatting
    date_for_sheet = _format_mmddyyyy(when)

    # ----- Step 1–3: DB transaction (pending) -----
    with SessionLocal() as db:
        game = _require_admin_for_game(db, public_code, admin_code)

        # We will only commit after Sheets append succeeds
        # Use a SAVEPOINT-like flow: flush changes, then call Sheets, then commit; on Sheets failure -> rollback.
        sess_id, affected_rows = _upsert_db_for_session(
            db=db,
            game=game,
            session_external_id=session_id,
            when=when,
            payload_json=game_data,
            validated_players=validated_players,
            game_number_for_meta=0,  # temp, will set real number after we peek at sheet
        )

        # Peek next game number from sheet (source of truth for numbering)
        game_number = _compute_next_game_number()

        # Update the stored JSON with ledger number before committing
        try:
            srow = db.execute(select(SessionModel).where(SessionModel.id == sess_id)).scalar_one()
            ej = dict(srow.end_session_json or {})
            ej.setdefault("meta", {})["ledger_game_number"] = game_number
            srow.end_session_json = ej
        except Exception:
            pass

        # ----- Step 4: append to Sheets (unrecoverable) -----
        try:
            append_result = _append_ledger_rows(game_number, date_for_sheet, validated_players)
        except Exception as e:
            db.rollback()
            log.error(f"Sheets append failed; DB rolled back. Error: {e}")
            raise

        # ----- Step 5: commit DB and write audit -----
        _write_audit(
            db=db,
            game=game,
            session_id=sess_id,
            admin_code=admin_code,
            action="IMPORT_LEDGER_SESSION",
            target="sessions",
            payload_before=None,
            payload_after={
                "session_external_id": session_id,
                "ledger_game_number": game_number,
                "players_count": len(validated_players),
            },
        )
        db.commit()

    # ----- Step 6: return -----
    return {
        "ok": True,
        "session_id": sess_id,
        "ledger": {
            "game_number": game_number,
            "updatedRange": append_result.get("updates", {}).get("updatedRange"),
            "rows_appended": append_result.get("updates", {}).get("updatedRows"),
        },
        "affected_player_summaries": affected_rows,
    }
