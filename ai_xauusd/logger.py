
import sqlite3


class DbLogger:

    def __init__(self, path="signals.db"):
        self.conn = sqlite3.connect(
            path,
            check_same_thread=False,
        )

        self._create_tables()

    def _create_tables(self):

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS candles (
                open_ts TEXT PRIMARY KEY,
                close_ts TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                tick_count INTEGER
            )
            """
        )

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS signals (
                ts TEXT,
                direction TEXT,
                entry REAL,
                sl REAL,
                tp REAL,
                score REAL,
                confidence TEXT,
                reason TEXT,
                setup_key TEXT
            )
            """
        )

        self.conn.commit()

    def candle(self, candle):

        self.conn.execute(
            """
            INSERT OR REPLACE INTO candles (
                open_ts,
                close_ts,
                open,
                high,
                low,
                close,
                tick_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candle.open_ts.isoformat(),
                candle.close_ts.isoformat(),
                candle.open,
                candle.high,
                candle.low,
                candle.close,
                candle.tick_count,
            ),
        )

        self.conn.commit()

    def signal(self, signal):

        self.conn.execute(
            """
            INSERT INTO signals (
                ts,
                direction,
                entry,
                sl,
                tp,
                score,
                confidence,
                reason,
                setup_key
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal.ts.isoformat(),
                signal.direction,
                signal.entry,
                signal.sl,
                signal.tp,
                signal.score,
                signal.confidence,
                signal.reason,
                signal.setup_key,
            ),
        )

        self.conn.commit()

    def recent_candles(self, limit=100):

        rows = self.conn.execute(
            """
            SELECT
                open_ts,
                close_ts,
                open,
                high,
                low,
                close,
                tick_count
            FROM candles
            ORDER BY open_ts DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        rows.reverse()

        from datetime import datetime

        from .models import Candle

        return [
            Candle(
                datetime.fromisoformat(row[0]),
                datetime.fromisoformat(row[1]),
                row[2],
                row[3],
                row[4],
                row[5],
                row[6],
            )
            for row in rows
        ]
