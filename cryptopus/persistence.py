import sqlite3
import threading
from datetime import datetime
from typing import Dict, List

from cryptopus.config import Order, Position


class TradeStore:
    def __init__(self, db_path: str = "cryptopus.db") -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        self._create_tables()

    def _create_tables(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    price REAL NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT NOT NULL,
                    exchange_id TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    symbol TEXT PRIMARY KEY,
                    amount REAL NOT NULL,
                    avg_price REAL NOT NULL,
                    realized_pnl REAL NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS daily_pnl (
                    date TEXT PRIMARY KEY,
                    pnl REAL NOT NULL
                )
            """)
            self._conn.commit()

    def save_order(self, order: Order) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO orders (ts, symbol, side, price, amount, status, exchange_id) VALUES (?,?,?,?,?,?,?)",
                (order.ts.isoformat(), order.symbol, order.side, order.price, order.amount, order.status, order.exchange_id),
            )
            self._conn.commit()

    def load_orders(self, limit: int = 200) -> List[Order]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT ts, symbol, side, price, amount, status, exchange_id FROM orders ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        result = []
        for row in reversed(rows):
            result.append(Order(
                ts=datetime.fromisoformat(row[0]),
                symbol=row[1],
                side=row[2],
                price=row[3],
                amount=row[4],
                status=row[5],
                exchange_id=row[6],
            ))
        return result

    def save_position(self, pos: Position) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO positions (symbol, amount, avg_price, realized_pnl) VALUES (?,?,?,?)",
                (pos.symbol, pos.amount, pos.avg_price, pos.realized_pnl),
            )
            self._conn.commit()

    def load_positions(self) -> Dict[str, Position]:
        with self._lock:
            rows = self._conn.execute("SELECT symbol, amount, avg_price, realized_pnl FROM positions").fetchall()
        return {r[0]: Position(symbol=r[0], amount=r[1], avg_price=r[2], realized_pnl=r[3]) for r in rows}

    def save_daily_pnl(self, date_str: str, pnl: float) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO daily_pnl (date, pnl) VALUES (?,?)",
                (date_str, pnl),
            )
            self._conn.commit()

    def load_daily_pnl(self, date_str: str) -> float:
        with self._lock:
            row = self._conn.execute("SELECT pnl FROM daily_pnl WHERE date=?", (date_str,)).fetchone()
        return row[0] if row else 0.0
