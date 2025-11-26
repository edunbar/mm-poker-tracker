# services/session_ingestion_service.py
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple

from sqlalchemy import select, func, text, delete
from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import (
    Game, Player, GamePlayer,
    Session as SessionModel,
    SessionPlayerSummary,
    AuditLog,
)
from services.metrics_service import log_metric

# Database-only implementation (Google Sheets removed)

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
def _fetch_name_map(db: Session) -> Dict[str, str]:
    """
    Read from players table and build {external_id: display_name} for players that have external_id.
    """
    players = db.execute(
        select(Player.external_id, Player.display_name)
        .where(Player.external_id.isnot(None))
    ).all()
    
    id_to_name: Dict[str, str] = {}
    for external_id, display_name in players:
        if external_id and external_id.strip():
            id_to_name[external_id.strip()] = display_name.strip()
    
    return id_to_name


def _compute_next_game_number(db: Session, game_id: str) -> int:
    """Get the next game number for this game from the database."""
    max_game_number = db.execute(
        text("SELECT MAX(game_number) FROM sessions WHERE game_id = :game_id"),
        {"game_id": game_id}
    ).scalar()
    return (max_game_number or 0) + 1


# _append_ledger_rows function removed - no longer needed without Google Sheets


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
    manual_game_number: int | None = None,
    session_type: str = "pokernow",
    session_name: str | None = None,
    ledger_csv_content: str | None = None,
    ended_at: datetime | None = None,
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
        # Use manual game number or calculate the next one
        if manual_game_number is not None:
            # Check if the manual game number already exists in this game
            existing_session = db.execute(
                select(SessionModel).where(
                    SessionModel.game_id == game.id,
                    SessionModel.game_number == manual_game_number
                )
            ).scalar_one_or_none()
            
            if existing_session:
                raise ValueError(f"Game number {manual_game_number} already exists. Please delete the existing game {manual_game_number} first or choose a different number.")
            
            game_number = manual_game_number
        else:
            max_game_number = db.execute(
                text("SELECT MAX(game_number) FROM sessions WHERE game_id = :game_id"),
                {"game_id": str(game.id)}
            ).scalar()
            game_number = (max_game_number or 0) + 1
        
        sess = SessionModel(
            game_id=game.id,
            external_id=session_external_id,
            session_type=session_type,
            session_name=session_name,
            game_number=game_number,
            started_at=when,
            ended_at=ended_at,
            end_session_json=payload_json,   # keep raw snapshot
            ledger_csv_content=ledger_csv_content,
        )
        db.add(sess)
        db.flush()
    else:
        # Update existing session
        sess.started_at = sess.started_at or when
        sess.ended_at = sess.ended_at or ended_at
        # Update game number if manual override is provided
        if manual_game_number is not None:
            # Check if the manual game number already exists in this game
            existing_session = db.execute(
                select(SessionModel).where(
                    SessionModel.game_id == game.id,
                    SessionModel.game_number == manual_game_number,
                    SessionModel.id != sess.id
                )
            ).scalar_one_or_none()

            if existing_session:
                raise ValueError(f"Game number {manual_game_number} already exists. Please delete the existing game {manual_game_number} first or choose a different number.")

            sess.game_number = manual_game_number
        sess.end_session_json = payload_json
        if ledger_csv_content:
            sess.ledger_csv_content = ledger_csv_content

    # Optional: store ledger game number in session JSON meta if you later add a meta column; for now store into end_session_json
    try:
        j = dict(sess.end_session_json or {})
        j.setdefault("meta", {})["ledger_game_number"] = game_number_for_meta
        sess.end_session_json = j
    except Exception:
        # ignore if JSONB merge fails for some reason
        pass

    # Clear existing summaries for this session to prevent duplicate key errors
    db.execute(
        delete(SessionPlayerSummary).where(SessionPlayerSummary.session_id == sess.id)
    )
    db.flush()  # Ensure delete is executed before inserts
    
    # Deduplicate players by external_id or display_name to prevent duplicate insertions
    seen_players = set()
    unique_players = []
    for p in validated_players:
        ext_pid = (p.get("id") or "").strip() or None
        display_name = (p.get("validated_name") or (p.get("names")[0] if p.get("names") else "Unknown")).strip()

        # Create a unique key based on external_id or normalized display_name
        # Both external_id and display_name are normalized to lowercase for case-insensitive matching
        unique_key = ext_pid.lower() if ext_pid else display_name.lower()

        if unique_key not in seen_players:
            seen_players.add(unique_key)
            unique_players.append(p)
    
    # Summaries
    affected = 0
    for p in unique_players:
        ext_pid = (p.get("id") or "").strip() or None
        names = p.get("names") or []
        display_name = (p.get("validated_name") or (names[0] if names else "Unknown")).strip()

        # Find player by display_name (case-insensitive) within this game only
        # Does NOT use external_id for matching to avoid duplicates when
        # same person joins with different PokerNow accounts
        player = db.execute(
            select(Player)
            .join(GamePlayer, Player.id == GamePlayer.player_id)
            .where(
                GamePlayer.game_id == game.id,
                func.lower(Player.display_name) == display_name.lower()
            )
        ).scalar_one_or_none()

        # If not found, create new player (still store external_id for reference)
        if not player:
            player = Player(display_name=display_name, external_id=ext_pid)
            db.add(player)
            db.flush()

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

        # Server-side validation: always recalculate net from components
        calculated_net = cash_out + in_game - buy_in
        frontend_net = p.get("net")

        # Log warning if frontend sent incorrect net value (helps detect bugs)
        if frontend_net is not None:
            frontend_net_int = int(frontend_net)
            if frontend_net_int != calculated_net:
                log.warning(
                    f"Frontend net mismatch for player {display_name}: "
                    f"frontend={frontend_net_int} cents (${frontend_net_int/100:.2f}), "
                    f"calculated={calculated_net} cents (${calculated_net/100:.2f}), "
                    f"session={session_external_id}"
                )

        # Always use calculated value, never trust frontend
        net = calculated_net

        # Add summary (we cleared all existing ones above)
        db.add(SessionPlayerSummary(
            session_id=sess.id,
            player_id=player.id,
            buy_in_sum=buy_in,       # chips in DB
            cash_out_sum=cash_out,
            in_game=in_game,
            net=net,
            names=names or [display_name],
        ))
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
def ingest_session(
    *,
    public_code: str,
    admin_code: str,
    session_id: str,            # PokerNow sessionId (required)
    game_data: Dict[str, Any],  # payload with playersInfos as dict
    date_iso: str | None = None, # optional ISO date, uses today if None
    manual_game_number: int | None = None,  # optional manual override for game number
    session_type: str = "pokernow",  # 'pokernow' | 'live'
    ledger_csv_content: str | None = None  # optional ledger CSV content from PokerNow
) -> Dict[str, Any]:
    """
    End-to-end:
      1) Validate admin for game
      2) Validate all players using database mappings (with fallbacks)
      3) Begin DB txn and upsert everything
      4) Compute next game number from database
      5) Commit DB; write audit; return result
    """
    # ----- Step 0: validate game first (404 takes precedence over 400) -----
    with SessionLocal() as db:
        game = _require_admin_for_game(db, public_code, admin_code)

        # ----- Step 1: normalize inputs -----
        players = _players_dict_to_list(game_data.get("playersInfos", {}))
        if not players:
            raise ValueError("No players found in payload")

        # Get validated name mappings but don't require them
        id_to_name = _fetch_name_map(db)

        # Attach validated_name into working copy, with fallbacks
        validated_players: List[Dict[str, Any]] = []
        for p in players:
            pid = p.get("id")
            vp = dict(p)
            
            # Priority order: validated_name from payload -> name mapping -> first name from names list -> player ID
            names_list = p.get("names", [])
            first_name = names_list[0] if names_list else ""
            
            validated_name = (
                p.get("validated_name") or 
                id_to_name.get(pid, "") or
                first_name or
                pid or
                "Unknown Player"
            )
            vp["validated_name"] = validated_name
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

        # Extract end date from game data
        ended_at = None
        ended_at_iso = game_data.get("endedAt")
        if ended_at_iso:
            try:
                ended_at = datetime.fromisoformat(ended_at_iso)
            except Exception:
                ended_at = when  # Default to start date if parsing fails

        # For Sheets date formatting
        date_for_sheet = _format_mmddyyyy(when)

        # Extract session name from game data for live games
        session_name_from_data = game_data.get("sessionName") if session_type == "live" else None
        
        # Use manual game number if provided, otherwise compute from database
        if manual_game_number is not None:
            game_number = manual_game_number
        else:
            # Get next game number from database
            game_number = _compute_next_game_number(db, str(game.id))
        
        sess_id, affected_rows = _upsert_db_for_session(
            db=db,
            game=game,
            session_external_id=session_id,
            when=when,
            payload_json=game_data,
            validated_players=validated_players,
            game_number_for_meta=game_number,
            manual_game_number=manual_game_number,
            session_type=session_type,
            session_name=session_name_from_data,
            ledger_csv_content=ledger_csv_content,
            ended_at=ended_at,
        )

        # Update the stored JSON with ledger number
        try:
            srow = db.execute(select(SessionModel).where(SessionModel.id == sess_id)).scalar_one()
            ej = dict(srow.end_session_json or {})
            ej.setdefault("meta", {})["ledger_game_number"] = game_number
            srow.end_session_json = ej
        except Exception:
            pass

        # ----- Step 4: commit DB and write audit -----
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

        # Log business metric
        log_metric("session_uploaded", {
            "game_id": str(game.id),
            "public_code": public_code,
            "session_id": session_id,
            "players_count": affected_rows
        })

        # Invalidate cache for this game (use v2 service)
        from services.game_summary_service_v2 import invalidate_game_cache
        invalidate_game_cache(public_code)

        # ----- Step 5: Process poker statistics if this is a PokerNow session -----
        statistics_processed = False
        try:
            if session_type == "pokernow" and ledger_csv_content:
                from services.poker_statistics_service import PokerStatisticsProcessor
                processor = PokerStatisticsProcessor(db)
                stats_result = processor.process_session_statistics(sess_id)
                statistics_processed = True
                log.info(f"Processed statistics for session {sess_id}: {stats_result}")
        except Exception as e:
            # Don't fail the entire ingestion if statistics processing fails
            log.warning(f"Failed to process statistics for session {sess_id}: {e}")

        # ----- Step 6: return -----
        return {
            "success": True,
            "session_id": session_id,  # Return the external session_id passed in, not the internal DB UUID
            "ledger": {
                "game_number": game_number,
            },
            "players_processed": affected_rows,
            "statistics_processed": statistics_processed,
        }
