#!/usr/bin/env python3

import sys
sys.path.insert(0, 'src')

from services.payment_service_v2 import PaymentService
from db.database import SessionLocal, engine
from db.models import Game, Player, Session, SessionPlayerSummary, PaymentBalance
from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import text

def debug_poker_winnings():
    print("=== DEBUGGING POKER WINNINGS CALCULATION ===")

    # Clean database
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM payment_transactions"))
        conn.execute(text("DELETE FROM payment_balances"))
        conn.execute(text("DELETE FROM session_player_summaries"))
        conn.execute(text("DELETE FROM sessions"))
        conn.execute(text("DELETE FROM game_players"))
        conn.execute(text("DELETE FROM players"))
        conn.execute(text("DELETE FROM games"))
        conn.commit()

    # Create test data manually
    with SessionLocal() as db:
        # Create game
        game = Game(
            public_code=f"DEBUG{uuid4().hex[:6].upper()}",
            admin_code=f"admin-{uuid4()}",
            title="Debug Game"
        )
        db.add(game)
        db.flush()

        # Create 3 players
        players = []
        for i in range(3):
            player = Player(
                external_id=f"debug_player_{i}@test",
                display_name=f"Player {i+1}",
                is_verified=True
            )
            db.add(player)
            players.append(player)

        db.flush()

        # Create session
        session = Session(
            game_id=game.id,
            external_id=f"debug_session_{uuid4().hex[:8]}",
            game_number=1,
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc)
        )
        db.add(session)
        db.flush()

        # Create poker results that sum to ZERO
        poker_results = [5000, -2000, -3000]  # cents
        print(f"Expected poker results: {poker_results}")
        print(f"Sum of poker results: {sum(poker_results)}")

        for i, player in enumerate(players):
            summary = SessionPlayerSummary(
                session_id=session.id,
                player_id=player.id,
                buy_in_sum=10000,  # $100
                cash_out_sum=10000 + poker_results[i],
                in_game=0,
                net=poker_results[i],
                names=[player.display_name]
            )
            db.add(summary)

        db.commit()
        print(f"Game ID: {game.id}")

        # Test v1 service first
        from services.payment_service import PaymentService as PaymentServiceV1
        service_v1 = PaymentServiceV1()
        summaries_v1 = service_v1.get_payment_summary(str(game.id))

        print(f"\nV1 Service returned {len(summaries_v1)} summaries:")
        total_poker_v1 = Decimal("0")
        for s in summaries_v1:
            print(f"  {s.player_name}: poker_net=${s.poker_net_winnings}")
            total_poker_v1 += s.poker_net_winnings

        print(f"V1 Total poker winnings: ${total_poker_v1}")

        # Now test v2 service
        service = PaymentService()
        summaries = service.get_payment_summary(str(game.id))

        print(f"\nV2 Service returned {len(summaries)} summaries:")
        total_poker = Decimal("0")
        for s in summaries:
            print(f"  {s.player_name}: poker_net=${s.poker_net_winnings}")
            total_poker += s.poker_net_winnings

        print(f"V2 Total poker winnings: ${total_poker}")
        print(f"Expected total: $0.00")

        # Check what's in the database directly
        print(f"\n=== DIRECT DATABASE CHECK ===")
        balances = db.query(PaymentBalance).filter(PaymentBalance.game_id == game.id).all()
        print(f"Found {len(balances)} balance records:")
        for balance in balances:
            poker_dollars = Decimal(balance.poker_net_winnings) / 100
            print(f"  Balance record: player_id={balance.player_id}, poker_net=${poker_dollars}")

if __name__ == "__main__":
    debug_poker_winnings()