# services/summary_service.py
from sqlalchemy import text
from db.database import SessionLocal
from typing import Dict, List, Any
from functools import lru_cache
import time
import logging
from middleware.performance_monitor import monitor_performance, record_cache_hit, record_cache_miss

# Simple in-memory cache for analytics data
_analytics_cache = {}
_cache_ttl = 300  # 5 minutes TTL

def _get_cache_key(public_code: str, query_type: str) -> str:
    """Generate cache key for the given public code and query type."""
    return f"{query_type}:{public_code}"

def _is_cache_valid(cache_entry: Dict) -> bool:
    """Check if cache entry is still valid based on TTL."""
    return time.time() - cache_entry['timestamp'] < _cache_ttl

def _get_from_cache(cache_key: str) -> Dict[str, Any]:
    """Get data from cache if valid, otherwise return None."""
    if cache_key in _analytics_cache:
        entry = _analytics_cache[cache_key]
        if _is_cache_valid(entry):
            logging.debug(f"Cache hit for {cache_key}")
            # Record cache hit for monitoring
            cache_type = cache_key.split(':')[0]
            record_cache_hit(cache_type)
            return entry['data']
        else:
            # Remove expired entry
            del _analytics_cache[cache_key]
            logging.debug(f"Cache expired for {cache_key}")

    # Record cache miss for monitoring
    cache_type = cache_key.split(':')[0]
    record_cache_miss(cache_type)
    return None

def _set_cache(cache_key: str, data: Dict[str, Any]) -> None:
    """Store data in cache with timestamp."""
    _analytics_cache[cache_key] = {
        'data': data,
        'timestamp': time.time()
    }
    logging.debug(f"Cached data for {cache_key}")

def invalidate_game_cache(public_code: str) -> None:
    """Invalidate all cached data for a specific game."""
    keys_to_remove = []
    for key in _analytics_cache.keys():
        if key.endswith(f":{public_code}"):
            keys_to_remove.append(key)

    for key in keys_to_remove:
        del _analytics_cache[key]
        logging.debug(f"Invalidated cache for {key}")

def clear_all_cache() -> None:
    """Clear entire analytics cache."""
    global _analytics_cache
    _analytics_cache = {}
    logging.debug("Cleared entire analytics cache")

@monitor_performance('summary')
def get_player_summaries(public_code: str):
    # Check cache first
    cache_key = _get_cache_key(public_code, "summaries")
    cached_data = _get_from_cache(cache_key)
    if cached_data is not None:
        return cached_data

    # Get game title
    with SessionLocal() as db:
        game_title_sql = text("SELECT title FROM games WHERE public_code = :public_code LIMIT 1;")
        game_title_result = db.execute(game_title_sql, {"public_code": public_code}).fetchone()
        title = game_title_result[0] if game_title_result and game_title_result[0] else None

        SQL = text('''
            WITH base AS (
                SELECT
                    p.id                         AS player_id,
                    p.display_name               AS player,
                    SUM(sps.buy_in_sum)          AS buy_in_chips,
                    SUM(sps.cash_out_sum)        AS cash_out_chips,
                    SUM(sps.in_game)             AS in_game_chips,
                    COUNT(DISTINCT s.id)         AS games_played
                FROM session_player_summaries sps
                JOIN sessions s      ON s.id = sps.session_id
                JOIN games g         ON g.id = s.game_id
                JOIN players p       ON p.id = sps.player_id
                WHERE g.public_code = :public_code
                GROUP BY p.id, p.display_name
            ),
            calc AS (
                SELECT
                    player_id,
                    player,
                    buy_in_chips,
                    cash_out_chips,
                    in_game_chips,
                    games_played,
                    (cash_out_chips + in_game_chips - buy_in_chips)       AS total_net_chips
                FROM base
            )
            SELECT
                player                                        AS "player",
                DENSE_RANK() OVER (ORDER BY total_net_chips DESC)    AS "rank",
                ROUND(buy_in_chips/100.0, 2)                  AS "buyIn",
                ROUND((cash_out_chips + in_game_chips)/100.0, 2) AS "cashOut",
                ROUND(total_net_chips/100.0, 2)               AS "net",
                games_played                                  AS "gamesPlayed"
            FROM calc
            ORDER BY "rank", "player";
            ''')
        rows = db.execute(SQL, {"public_code": public_code}).mappings().all()
        result = {"title": title, "rows": [dict(r) for r in rows]}

        # Cache the result
        _set_cache(cache_key, result)
        return result


@monitor_performance('analytics')
def get_player_analytics(public_code: str) -> Dict[str, Any]:
    """
    Get advanced analytics including streak calculations for a game.
    Returns both basic summaries and calculated streaks.
    """
    # Check cache first (temporarily disabled to force refresh)
    # cache_key = _get_cache_key(public_code, "analytics")
    # cached_data = _get_from_cache(cache_key)
    # if cached_data is not None:
    #     return cached_data

    with SessionLocal() as db:
        # Simplified approach - get basic data and use Python for current streaks
        analytics_sql = text('''
            WITH player_sessions AS (
                SELECT
                    p.id AS player_id,
                    p.display_name AS player_name,
                    s.game_number,
                    sps.net,
                    sps.buy_in_sum,
                    CASE WHEN sps.net > 0 THEN 1 ELSE 0 END AS is_win,
                    CASE WHEN sps.net < 0 THEN 1 ELSE 0 END AS is_loss,
                    ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY s.game_number) AS session_order
                FROM session_player_summaries sps
                JOIN sessions s ON s.id = sps.session_id
                JOIN games g ON g.id = s.game_id
                JOIN players p ON p.id = sps.player_id
                WHERE g.public_code = :public_code
            ),
            -- Use islands-and-gaps for longest streaks with net calculation
            win_streak_groups AS (
                SELECT
                    player_id,
                    session_order,
                    net,
                    session_order - ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY session_order) AS grp
                FROM player_sessions
                WHERE is_win = 1
            ),
            win_streaks AS (
                SELECT
                    player_id,
                    COUNT(*) AS streak_length,
                    SUM(net) AS streak_net,
                    MIN(session_order) AS streak_start,
                    MAX(session_order) AS streak_end
                FROM win_streak_groups
                GROUP BY player_id, grp
            ),
            loss_streak_groups AS (
                SELECT
                    player_id,
                    session_order,
                    net,
                    session_order - ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY session_order) AS grp
                FROM player_sessions
                WHERE is_loss = 1
            ),
            loss_streaks AS (
                SELECT
                    player_id,
                    COUNT(*) AS streak_length,
                    SUM(net) AS streak_net,
                    MIN(session_order) AS streak_start,
                    MAX(session_order) AS streak_end
                FROM loss_streak_groups
                GROUP BY player_id, grp
            ),
            player_totals AS (
                SELECT
                    player_id,
                    MAX(player_name) AS player_name,
                    COUNT(*) AS total_games,
                    SUM(net) AS total_net,
                    SUM(buy_in_sum) AS total_buy_in,
                    SUM(is_win) AS total_wins,
                    SUM(is_loss) AS total_losses
                FROM player_sessions
                GROUP BY player_id
            )
            SELECT
                pt.player_id,
                pt.player_name,
                pt.total_games,
                pt.total_net,
                pt.total_buy_in,
                pt.total_wins,
                pt.total_losses,
                COALESCE(MAX(ws.streak_length), 0) AS longest_winning_streak,
                COALESCE(MAX(ls.streak_length), 0) AS longest_losing_streak,
                -- Get the net for the longest winning streak
                COALESCE(
                    (SELECT ws2.streak_net
                     FROM win_streaks ws2
                     WHERE ws2.player_id = pt.player_id
                     ORDER BY ws2.streak_length DESC, ws2.streak_net DESC
                     LIMIT 1), 0
                ) AS longest_winning_streak_net,
                -- Get the net for the longest losing streak
                COALESCE(
                    (SELECT ls2.streak_net
                     FROM loss_streaks ls2
                     WHERE ls2.player_id = pt.player_id
                     ORDER BY ls2.streak_length DESC, ABS(ls2.streak_net) DESC
                     LIMIT 1), 0
                ) AS longest_losing_streak_net,
                CASE
                    WHEN NOT EXISTS (
                        SELECT 1 FROM player_sessions ps
                        WHERE ps.player_id = pt.player_id AND ps.net > 0
                    )
                    THEN true
                    ELSE false
                END AS never_profitable
            FROM player_totals pt
            LEFT JOIN win_streaks ws ON ws.player_id = pt.player_id
            LEFT JOIN loss_streaks ls ON ls.player_id = pt.player_id
            GROUP BY pt.player_id, pt.player_name, pt.total_games, pt.total_net, pt.total_buy_in, pt.total_wins, pt.total_losses
        ''')

        results = db.execute(analytics_sql, {"public_code": public_code}).mappings().all()

        if not results:
            return {"analytics": {}}

        # Get session data for current streak calculation
        session_data_sql = text('''
            SELECT
                p.id AS player_id,
                s.game_number,
                sps.net,
                CASE WHEN sps.net > 0 THEN 1 ELSE 0 END AS is_win,
                CASE WHEN sps.net < 0 THEN 1 ELSE 0 END AS is_loss
            FROM session_player_summaries sps
            JOIN sessions s ON s.id = sps.session_id
            JOIN games g ON g.id = s.game_id
            JOIN players p ON p.id = sps.player_id
            WHERE g.public_code = :public_code
            ORDER BY p.id, s.game_number
        ''')

        session_results = db.execute(session_data_sql, {"public_code": public_code}).mappings().all()

        # Group sessions by player
        player_sessions = {}
        for session in session_results:
            player_id = str(session['player_id'])
            if player_id not in player_sessions:
                player_sessions[player_id] = []
            player_sessions[player_id].append(session)

        # Convert results to expected format and calculate current streaks
        player_analytics = {}
        for row in results:
            player_id = str(row['player_id'])

            # Calculate current streaks using Python
            current_winning_streak = 0
            current_losing_streak = 0

            if player_id in player_sessions:
                sessions = player_sessions[player_id]
                # Count backwards from most recent session
                for session in reversed(sessions):
                    if session['is_win'] == 1:
                        if current_losing_streak == 0:  # Still in winning streak
                            current_winning_streak += 1
                        else:
                            break  # Hit a loss, stop counting wins
                    elif session['is_loss'] == 1:
                        if current_winning_streak == 0:  # Still in losing streak
                            current_losing_streak += 1
                        else:
                            break  # Hit a win, stop counting losses
                    # If net == 0, break the streak
                    else:
                        break

            player_analytics[player_id] = {
                'player_name': row['player_name'],
                'total_games': row['total_games'],
                'total_wins': row['total_wins'],
                'total_losses': row['total_losses'],
                'current_losing_streak': current_losing_streak,
                'longest_losing_streak': row['longest_losing_streak'],
                'current_winning_streak': current_winning_streak,
                'longest_winning_streak': row['longest_winning_streak'],
                'never_profitable': row['never_profitable'],
                'total_net': row['total_net'],
                'total_buy_in': row['total_buy_in'],
                'longest_winning_streak_net': row['longest_winning_streak_net'],
                'longest_losing_streak_net': row['longest_losing_streak_net'],
            }

        result = {"analytics": player_analytics}

        # Cache the result (temporarily disabled)
        # _set_cache(cache_key, result)
        return result


@monitor_performance('session_extremes')
def get_session_extremes(public_code: str) -> Dict[str, Any]:
    """
    Get the actual best and worst single session performances.
    Returns real max/min values from individual sessions.
    """
    # Check cache first (temporarily disabled to force refresh)
    # cache_key = _get_cache_key(public_code, "session_extremes")
    # cached_data = _get_from_cache(cache_key)
    # if cached_data is not None:
    #     return cached_data

    with SessionLocal() as db:
        # Get the best and worst single session performances
        extremes_sql = text('''
            WITH session_performances AS (
                SELECT
                    p.display_name AS player_name,
                    s.game_number,
                    s.session_name,
                    s.external_id,
                    sps.net,
                    sps.buy_in_sum,
                    sps.cash_out_sum,
                    sps.in_game,
                    ROW_NUMBER() OVER (ORDER BY sps.net DESC) AS best_rank,
                    ROW_NUMBER() OVER (ORDER BY sps.net ASC) AS worst_rank
                FROM session_player_summaries sps
                JOIN sessions s ON s.id = sps.session_id
                JOIN games g ON g.id = s.game_id
                JOIN players p ON p.id = sps.player_id
                WHERE g.public_code = :public_code
            ),
            combined_results AS (
                SELECT
                    'best' as type,
                    player_name,
                    game_number,
                    session_name,
                    external_id,
                    net,
                    buy_in_sum,
                    cash_out_sum,
                    in_game
                FROM session_performances
                WHERE best_rank <= 25 AND net > 0

                UNION ALL

                SELECT
                    'worst' as type,
                    player_name,
                    game_number,
                    session_name,
                    external_id,
                    net,
                    buy_in_sum,
                    cash_out_sum,
                    in_game
                FROM session_performances
                WHERE worst_rank <= 25 AND net < 0
            )
            SELECT * FROM combined_results
            ORDER BY
                type DESC,
                CASE WHEN type = 'best' THEN -net ELSE net END ASC
        ''')

        results = db.execute(extremes_sql, {"public_code": public_code}).mappings().all()

        if not results:
            return {"best_sessions": [], "worst_sessions": []}

        best_sessions = []
        worst_sessions = []

        for row in results:
            session_data = {
                'player_name': row['player_name'],
                'game_number': row['game_number'],
                'session_name': row['session_name'],
                'external_id': row['external_id'],
                'net': row['net'],
                'buy_in_sum': row['buy_in_sum'],
                'cash_out_sum': row['cash_out_sum'],
                'in_game': row['in_game']
            }

            if row['type'] == 'best':
                best_sessions.append(session_data)
            else:
                worst_sessions.append(session_data)

        result = {
            "best_sessions": best_sessions,
            "worst_sessions": worst_sessions
        }

        # Cache the result (temporarily disabled)
        # _set_cache(cache_key, result)
        return result




class GameSummaryService:
    """Wrapper class for game summary functions to maintain compatibility."""

    def __init__(self, db_session=None):
        self.db_session = db_session

    def get_player_summaries(self, public_code: str):
        return get_player_summaries(public_code)

    def get_player_analytics(self, public_code: str):
        return get_player_analytics(public_code)

    def get_session_extremes(self, public_code: str):
        return get_session_extremes(public_code)
