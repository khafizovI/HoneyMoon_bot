"""Demo buyurtmalar yaratish — klientga ko'rsatish uchun."""
import asyncio

import database as db
from config import ADMIN_IDS


async def seed():
    await db.init_db()
    admin_id = ADMIN_IDS[0] if ADMIN_IDS else 1

    demos = [
        ("Dori-Darmon aptekasi", "Chilonzor 5-kvartal", 120, 85000),
        ("Shifokorlik markazi", "Yunusobod 3-mavze", 80, 95000),
        ("Salomatlik dorixonasi", "Sergeli 2-kvartal", 200, 75000),
        ("Medika Plus", "Mirzo Ulug'bek", 50, 120000),
    ]

    for name, loc, qty, price in demos:
        oid = await db.create_order(name, loc, qty, price, admin_id, "Demo buyurtma")
        print(f"  #{oid} — {name} — {qty * price:,} so'm")

    print("\n✅ Demo buyurtmalar yaratildi!")


if __name__ == "__main__":
    asyncio.run(seed())
