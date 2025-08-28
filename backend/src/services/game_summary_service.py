# services/summary_service.py
from sqlalchemy import text
from db.database import SessionLocal

def get_player_summaries(public_code: str):
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
                    (cash_out_chips - buy_in_chips)                       AS realized_net_chips
                FROM base
            )
            SELECT
                player                                        AS "player",
                DENSE_RANK() OVER (ORDER BY realized_net_chips DESC)    AS "rank",
                ROUND(buy_in_chips/100.0, 2)                  AS "buyIn",
                ROUND(cash_out_chips/100.0, 2)                AS "cashOut",
                ROUND(realized_net_chips/100.0, 2)            AS "net",
                games_played                                  AS "gamesPlayed"
            FROM calc
            ORDER BY "rank", "player";
            ''')
        rows = db.execute(SQL, {"public_code": public_code}).mappings().all()
        return {"title": title, "rows": [dict(r) for r in rows]}