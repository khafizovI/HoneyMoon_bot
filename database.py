import aiosqlite
from datetime import datetime
from typing import Optional

from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                username TEXT,
                role TEXT NOT NULL DEFAULT 'delivery',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pharmacy_name TEXT NOT NULL,
                location TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                total_price REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                assigned_to INTEGER,
                picked_up_at TEXT,
                delivered_at TEXT,
                photo_file_id TEXT,
                photo_uploaded_at TEXT,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                notes TEXT,
                FOREIGN KEY (assigned_to) REFERENCES users(telegram_id),
                FOREIGN KEY (created_by) REFERENCES users(telegram_id)
            );
        """)
        await db.commit()

        for col, typedef in (("latitude", "REAL"), ("longitude", "REAL")):
            try:
                await db.execute(f"ALTER TABLE orders ADD COLUMN {col} {typedef}")
            except Exception:
                pass
        await db.commit()


async def get_user(telegram_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ? AND is_active = 1",
            (telegram_id,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def add_user(telegram_id: int, full_name: str, username: str, role: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO users
               (telegram_id, full_name, username, role, is_active, created_at)
               VALUES (?, ?, ?, ?, 1, ?)""",
            (telegram_id, full_name, username or "", role, datetime.now().isoformat()),
        )
        await db.commit()


async def remove_user(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_active = 0 WHERE telegram_id = ?",
            (telegram_id,),
        )
        await db.commit()


async def list_users(role: Optional[str] = None) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if role:
            query = "SELECT * FROM users WHERE is_active = 1 AND role = ? ORDER BY full_name"
            params = (role,)
        else:
            query = "SELECT * FROM users WHERE is_active = 1 ORDER BY role, full_name"
            params = ()
        async with db.execute(query, params) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def create_order(
    pharmacy_name: str,
    location: str,
    quantity: int,
    unit_price: float,
    created_by: int,
    notes: str = "",
    latitude: float | None = None,
    longitude: float | None = None,
) -> int:
    total = quantity * unit_price
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO orders
               (pharmacy_name, location, quantity, unit_price, total_price,
                status, created_by, created_at, notes, latitude, longitude)
               VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)""",
            (pharmacy_name, location, quantity, unit_price, total, created_by, now, notes, latitude, longitude),
        )
        await db.commit()
        return cur.lastrowid


async def get_order(order_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def list_orders(
    status: Optional[str] = None,
    assigned_to: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        conditions = []
        params: list = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if assigned_to is not None:
            conditions.append("(assigned_to = ? OR assigned_to IS NULL)")
            params.append(assigned_to)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT * FROM orders {where} ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        async with db.execute(query, params) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def count_orders(status: Optional[str] = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        if status:
            async with db.execute(
                "SELECT COUNT(*) FROM orders WHERE status = ?", (status,)
            ) as cur:
                row = await cur.fetchone()
        else:
            async with db.execute("SELECT COUNT(*) FROM orders") as cur:
                row = await cur.fetchone()
        return row[0] if row else 0


async def delete_order(order_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        await db.commit()
        return cur.rowcount > 0


async def assign_order(order_id: int, delivery_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET assigned_to = ?, status = 'assigned' WHERE id = ?",
            (delivery_id, order_id),
        )
        await db.commit()


async def mark_picked_up(order_id: int):
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET status = 'picked_up', picked_up_at = ? WHERE id = ?",
            (now, order_id),
        )
        await db.commit()


async def mark_delivered(order_id: int, photo_file_id: str):
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE orders SET status = 'delivered', delivered_at = ?,
               photo_file_id = ?, photo_uploaded_at = ? WHERE id = ?""",
            (now, photo_file_id, now, order_id),
        )
        await db.commit()


async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        stats = {}
        for status in ("pending", "assigned", "picked_up", "delivered"):
            async with db.execute(
                "SELECT COUNT(*), COALESCE(SUM(total_price), 0) FROM orders WHERE status = ?",
                (status,),
            ) as cur:
                row = await cur.fetchone()
                stats[status] = {"count": row[0], "total": row[1]}
        async with db.execute(
            "SELECT COALESCE(SUM(total_price), 0) FROM orders WHERE status != 'delivered'"
        ) as cur:
            row = await cur.fetchone()
            stats["in_transit_value"] = row[0] if row else 0
        return stats
