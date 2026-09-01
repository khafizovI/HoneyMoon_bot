from datetime import datetime

STATUS_LABELS = {
    "pending": "⏳ Omborda",
    "assigned": "📋 Tayinlangan",
    "picked_up": "🚚 Yo'lda",
    "delivered": "✅ Yetkazildi",
}

ROLE_LABELS = {
    "admin": "👑 Admin",
    "delivery": "🚚 Yetkazuvchi",
}


def fmt_money(amount: float) -> str:
    return f"{amount:,.0f} so'm".replace(",", " ")


def fmt_datetime(iso_str: str | None) -> str:
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return iso_str


def format_order_short(order: dict) -> str:
    status = STATUS_LABELS.get(order["status"], order["status"])
    return (
        f"#{order['id']} · {order['pharmacy_name']}\n"
        f"📍 {order['location']}\n"
        f"📦 {order['quantity']} dona × {fmt_money(order['unit_price'])}\n"
        f"💰 Jami: {fmt_money(order['total_price'])}\n"
        f"📊 {status}"
    )


def format_order_detail(order: dict) -> str:
    lines = [
        f"📋 <b>Buyurtma #{order['id']}</b>",
        "",
        f"🏥 <b>Apteka:</b> {order['pharmacy_name']}",
        f"📍 <b>Ko'cha:</b> {order['location']}",
        f"📦 <b>Miqdor:</b> {order['quantity']} dona",
        f"💵 <b>Narx (dona):</b> {fmt_money(order['unit_price'])}",
        f"💰 <b>Jami summa:</b> {fmt_money(order['total_price'])}",
        "",
        f"📊 <b>Holat:</b> {STATUS_LABELS.get(order['status'], order['status'])}",
    ]

    if order.get("picked_up_at"):
        lines.append(f"📤 Ombordan olingan: {fmt_datetime(order['picked_up_at'])}")

    if order.get("photo_uploaded_at"):
        lines.extend([
            "",
            f"📸 <b>Rasm yuklangan vaqt:</b> <b>{fmt_datetime(order['photo_uploaded_at'])}</b>",
        ])
    elif order["status"] == "delivered":
        lines.append("\n⚠️ Rasm vaqti yozilmagan")

    if order.get("delivered_at"):
        lines.append(f"✅ Yetkazilgan: {fmt_datetime(order['delivered_at'])}")

    if order.get("notes"):
        lines.extend(["", f"📝 Izoh: {order['notes']}"])

    lines.append(f"\n🕐 Yaratilgan: {fmt_datetime(order['created_at'])}")
    return "\n".join(lines)


def format_warehouse_order(order: dict) -> str:
    """Ombor ko'rinishi — faqat ko'cha nomi qalin, rasm vaqti ham qalin."""
    picked = "✅ Olib ketilgan" if order.get("picked_up_at") else "❌ Olib ketilmagan"
    street = order.get("location") or "—"
    lines = [
        f"#{order['id']} · <b>{order['pharmacy_name']}</b>",
        f"📍 <b>{street}</b>",
        f"📦 {order['quantity']} dona · {fmt_money(order['total_price'])}",
        f"📤 Ombor: {picked}",
    ]
    if order.get("picked_up_at"):
        lines.append(f"   ↳ {fmt_datetime(order['picked_up_at'])}")

    if order.get("photo_uploaded_at"):
        lines.append(
            f"📸 <b>Rasm yuklangan:</b> <b>{fmt_datetime(order['photo_uploaded_at'])}</b>"
        )
    else:
        lines.append("📸 Rasm: hali yuklanmagan")

    return "\n".join(lines)
