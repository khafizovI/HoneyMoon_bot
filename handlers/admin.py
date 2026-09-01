from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from keyboards import (
    admin_main_kb,
    cancel_kb,
    location_kb,
    confirm_order_kb,
    orders_list_kb,
    order_actions_admin_kb,
    assign_delivery_kb,
    delete_confirm_kb,
    users_list_kb,
    user_actions_kb,
    role_select_kb,
)
from states import AddOrder, AddUser
from geocode import get_street_name
from utils import format_order_detail, format_warehouse_order, fmt_money, ROLE_LABELS

router = Router()
PAGE_SIZE = 8


def is_admin(user: dict | None) -> bool:
    return user is not None and user["role"] == "admin"


async def get_admin(message_or_query) -> dict | None:
    uid = message_or_query.from_user.id
    user = await db.get_user(uid)
    return user if is_admin(user) else None


# ── Buyurtma qo'shish ──────────────────────────────────────────

@router.message(F.text == "➕ Buyurtma qo'shish")
async def add_order_start(message: Message, state: FSMContext):
    if not await get_admin(message):
        return
    await state.set_state(AddOrder.pharmacy_name)
    await message.answer(
        "🏥 <b>Apteka nomini kiriting:</b>\n\n<i>Masalan: Shifokorlik dorixonasi</i>",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )


@router.message(AddOrder.pharmacy_name, F.text == "❌ Bekor qilish")
@router.message(AddOrder.location, F.text == "❌ Bekor qilish")
@router.message(AddOrder.quantity, F.text == "❌ Bekor qilish")
@router.message(AddOrder.unit_price, F.text == "❌ Bekor qilish")
@router.message(AddOrder.notes, F.text == "❌ Bekor qilish")
async def add_order_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=admin_main_kb())


@router.message(AddOrder.pharmacy_name)
async def add_order_pharmacy(message: Message, state: FSMContext):
    await state.update_data(pharmacy_name=message.text.strip())
    await state.set_state(AddOrder.location)
    await message.answer(
        "📍 <b>Apteka lokatsiyasini yuboring</b>\n\n"
        "Quyidagi tugmani bosing va xaritadan joyni tanlang 👇",
        reply_markup=location_kb(),
        parse_mode="HTML",
    )


@router.message(AddOrder.location, F.location)
async def add_order_location(message: Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude
    wait_msg = await message.answer("⏳ Ko'cha nomi aniqlanmoqda...")

    street = await get_street_name(lat, lon)
    await state.update_data(location=street, latitude=lat, longitude=lon)
    await state.set_state(AddOrder.quantity)

    await wait_msg.edit_text(f"✅ Ko'cha: <b>{street}</b>", parse_mode="HTML")
    await message.answer(
        "📦 <b>Tovar sonini kiriting:</b>\n\n<i>Masalan: 50</i>",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )


@router.message(AddOrder.location)
async def add_order_location_invalid(message: Message):
    await message.answer(
        "❌ Matn emas — lokatsiya yuboring.\n"
        "📍 <b>Lokatsiyani yuborish</b> tugmasini bosing.",
        reply_markup=location_kb(),
        parse_mode="HTML",
    )


@router.message(AddOrder.quantity)
async def add_order_quantity(message: Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
        if qty <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Iltimos, musbat butun son kiriting.")
        return
    await state.update_data(quantity=qty)
    await state.set_state(AddOrder.unit_price)
    await message.answer("💵 <b>Bitta tovar narxini kiriting (so'm):</b>\n\n<i>Masalan: 85000</i>", parse_mode="HTML")


@router.message(AddOrder.unit_price)
async def add_order_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip().replace(" ", "").replace(",", ""))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Iltimos, to'g'ri narx kiriting.")
        return
    await state.update_data(unit_price=price)
    await state.set_state(AddOrder.notes)
    await message.answer(
        "📝 <b>Izoh (ixtiyoriy):</b>\n\nIzoh yo'q bo'lsa <b>-</b> yuboring.",
        parse_mode="HTML",
    )


@router.message(AddOrder.notes)
async def add_order_notes(message: Message, state: FSMContext):
    notes = "" if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()
    total = data["quantity"] * data["unit_price"]
    await state.update_data(notes=notes, total_price=total)

    summary = (
        "📋 <b>Buyurtmani tasdiqlang:</b>\n\n"
        f"🏥 Apteka: <b>{data['pharmacy_name']}</b>\n"
        f"📍 Ko'cha: <b>{data['location']}</b>\n"
        f"📦 Miqdor: {data['quantity']} dona\n"
        f"💵 Dona narxi: {fmt_money(data['unit_price'])}\n"
        f"💰 <b>Jami: {fmt_money(total)}</b>\n"
    )
    if notes:
        summary += f"📝 Izoh: {notes}\n"

    await state.set_state(AddOrder.confirm)
    await message.answer(summary, reply_markup=confirm_order_kb(), parse_mode="HTML")


@router.callback_query(F.data == "order:confirm")
async def add_order_confirm(callback: CallbackQuery, state: FSMContext):
    if not await get_admin(callback):
        return
    data = await state.get_data()
    order_id = await db.create_order(
        pharmacy_name=data["pharmacy_name"],
        location=data["location"],
        quantity=data["quantity"],
        unit_price=data["unit_price"],
        created_by=callback.from_user.id,
        notes=data.get("notes", ""),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
    )
    await state.clear()
    await callback.message.edit_text(
        f"✅ Buyurtma <b>#{order_id}</b> yaratildi!\n"
        f"💰 Summa: {fmt_money(data['total_price'])}",
        parse_mode="HTML",
    )
    await callback.message.answer("Admin panel:", reply_markup=admin_main_kb())
    await callback.answer()


@router.callback_query(F.data == "order:cancel")
async def add_order_cancel_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Bekor qilindi.")
    await callback.message.answer("Admin panel:", reply_markup=admin_main_kb())
    await callback.answer()


# ── Buyurtmalar ro'yxati ──────────────────────────────────────

@router.message(F.text == "📋 Buyurtmalar")
async def list_orders_cmd(message: Message):
    if not await get_admin(message):
        return
    await _show_orders_page(message, 0)


async def _show_orders_page(target, page: int, edit: bool = False):
    total = await db.count_orders()
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    orders = await db.list_orders(limit=PAGE_SIZE, offset=page * PAGE_SIZE)

    if not orders:
        text = "📋 Hozircha buyurtmalar yo'q."
        kb = None
    else:
        text = f"📋 <b>Buyurtmalar</b> ({total} ta) — sahifa {page + 1}/{total_pages}\n\nBatafsil ko'rish uchun bosing:"
        kb = orders_list_kb(orders, prefix="admin:order", page=page, total_pages=total_pages)

    if edit and hasattr(target, "edit_text"):
        await target.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin:order:page:"))
async def orders_page_cb(callback: CallbackQuery):
    if not await get_admin(callback):
        return
    page = int(callback.data.split(":")[-1])
    await _show_orders_page(callback.message, page, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:order:view:"))
async def order_view_from_list(callback: CallbackQuery):
    if not await get_admin(callback):
        return
    order_id = int(callback.data.split(":")[-1])
    await _show_order_detail(callback, order_id)


@router.callback_query(F.data.regexp(r"^admin:order:\d+$"))
async def order_view_cb(callback: CallbackQuery):
    if not await get_admin(callback):
        return
    order_id = int(callback.data.split(":")[-1])
    await _show_order_detail(callback, order_id)


async def _show_order_detail(callback: CallbackQuery, order_id: int):
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Buyurtma topilmadi", show_alert=True)
        return
    text = format_order_detail(order)
    if order.get("photo_file_id"):
        await callback.message.answer_photo(
            order["photo_file_id"],
            caption=f"📸 Yetkazish rasmi — #{order_id}",
        )
    await callback.message.edit_text(
        text,
        reply_markup=order_actions_admin_kb(order_id),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Ombor ──────────────────────────────────────────────────────

@router.message(F.text == "🏭 Ombor")
async def warehouse_view(message: Message):
    if not await get_admin(message):
        return
    orders = await db.list_orders(limit=100)
    if not orders:
        await message.answer("🏭 Omborda buyurtmalar yo'q.")
        return

    pending = [o for o in orders if not o.get("picked_up_at")]
    picked = [o for o in orders if o.get("picked_up_at") and o["status"] != "delivered"]
    delivered = [o for o in orders if o["status"] == "delivered"]

    lines = ["🏭 <b>OMBOR — HOLAT</b>", ""]

    if pending:
        lines.append(f"❌ <b>Olib ketilmagan ({len(pending)} ta):</b>")
        for o in pending:
            lines.append(format_warehouse_order(o))
            lines.append("")

    if picked:
        lines.append(f"🚚 <b>Yo'lda ({len(picked)} ta):</b>")
        for o in picked:
            lines.append(format_warehouse_order(o))
            lines.append("")

    if delivered:
        lines.append(f"✅ <b>Yetkazilgan ({len(delivered)} ta):</b>")
        for o in delivered[:10]:
            lines.append(format_warehouse_order(o))
            lines.append("")
        if len(delivered) > 10:
            lines.append(f"... va yana {len(delivered) - 10} ta")

    text = "\n".join(lines)
    if len(text) > 4000:
        chunks = []
        current = ["🏭 <b>OMBOR — HOLAT</b>", ""]
        for line in lines[2:]:
            if sum(len(l) for l in current) + len(line) > 3800:
                chunks.append("\n".join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            chunks.append("\n".join(current))
        for chunk in chunks:
            await message.answer(chunk, parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")


# ── Hisobot ────────────────────────────────────────────────────

@router.message(F.text == "📊 Hisobot")
async def stats_view(message: Message):
    if not await get_admin(message):
        return
    stats = await db.get_stats()
    text = (
        "📊 <b>HISOBOT — Honeymoon.uz</b>\n\n"
        f"⏳ Omborda: {stats['pending']['count']} ta · {fmt_money(stats['pending']['total'])}\n"
        f"📋 Tayinlangan: {stats['assigned']['count']} ta · {fmt_money(stats['assigned']['total'])}\n"
        f"🚚 Yo'lda: {stats['picked_up']['count']} ta · {fmt_money(stats['picked_up']['total'])}\n"
        f"✅ Yetkazilgan: {stats['delivered']['count']} ta · {fmt_money(stats['delivered']['total'])}\n\n"
        f"⚠️ <b>Qayerda pul 'yo'qolgan':</b>\n"
        f"Yetkazilmagan jami: <b>{fmt_money(stats['in_transit_value'])}</b>\n\n"
        "<i>Bu yerda qaysi buyurtmalar hali yetkazilmaganini ko'rasiz.</i>"
    )
    await message.answer(text, parse_mode="HTML")


# ── Xodimlar ───────────────────────────────────────────────────

@router.message(F.text == "👥 Xodimlar")
async def users_list_cmd(message: Message):
    if not await get_admin(message):
        return
    users = await db.list_users()
    if not users:
        await message.answer(
            "👥 Xodimlar yo'q. Quyidagi tugma orqali qo'shing:",
            reply_markup=users_list_kb([]),
        )
        return
    text = "👥 <b>Xodimlar ro'yxati:</b>\n\nBatafsil uchun bosing:"
    await message.answer(text, reply_markup=users_list_kb(users), parse_mode="HTML")


@router.callback_query(F.data == "admin:users")
async def users_list_cb(callback: CallbackQuery):
    if not await get_admin(callback):
        return
    users = await db.list_users()
    await callback.message.edit_text(
        "👥 <b>Xodimlar ro'yxati:</b>",
        reply_markup=users_list_kb(users),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin:add_user")
async def add_user_start(callback: CallbackQuery, state: FSMContext):
    if not await get_admin(callback):
        return
    await state.set_state(AddUser.telegram_id)
    await callback.message.answer(
        "👤 <b>Yangi xodim Telegram ID sini kiriting:</b>\n\n"
        "<i>ID ni @userinfobot orqali olish mumkin</i>",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AddUser.telegram_id, F.text == "❌ Bekor qilish")
async def add_user_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=admin_main_kb())


@router.message(AddUser.telegram_id)
async def add_user_id(message: Message, state: FSMContext):
    try:
        tid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ To'g'ri Telegram ID kiriting.")
        return
    await state.update_data(telegram_id=tid)
    await state.set_state(AddUser.role)
    await message.answer("Rolni tanlang:", reply_markup=role_select_kb())


@router.callback_query(F.data.startswith("role:"), AddUser.role)
async def add_user_role(callback: CallbackQuery, state: FSMContext):
    if not await get_admin(callback):
        return
    role = callback.data.split(":")[1]
    data = await state.get_data()
    await db.add_user(data["telegram_id"], f"User {data['telegram_id']}", "", role)
    await state.clear()
    await callback.message.edit_text(
        f"✅ Xodim qo'shildi!\n"
        f"ID: {data['telegram_id']}\n"
        f"Rol: {ROLE_LABELS.get(role, role)}",
        parse_mode="HTML",
    )
    await callback.message.answer("Admin panel:", reply_markup=admin_main_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("admin:user:"))
async def user_detail(callback: CallbackQuery):
    if not await get_admin(callback):
        return
    tid = int(callback.data.split(":")[-1])
    user = await db.get_user(tid)
    if not user:
        await callback.answer("Topilmadi", show_alert=True)
        return
    text = (
        f"👤 <b>{user['full_name']}</b>\n"
        f"ID: <code>{user['telegram_id']}</code>\n"
        f"Rol: {ROLE_LABELS.get(user['role'], user['role'])}"
    )
    await callback.message.edit_text(
        text, reply_markup=user_actions_kb(tid), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:remove_user:"))
async def remove_user_cb(callback: CallbackQuery):
    if not await get_admin(callback):
        return
    tid = int(callback.data.split(":")[-1])
    if tid == callback.from_user.id:
        await callback.answer("O'zingizni o'chira olmaysiz!", show_alert=True)
        return
    await db.remove_user(tid)
    await callback.message.edit_text("✅ Xodim o'chirildi.")
    await callback.answer()


# ── Tayinlash / O'chirish ──────────────────────────────────────

@router.callback_query(F.data.startswith("admin:assign:"))
async def assign_start(callback: CallbackQuery):
    if not await get_admin(callback):
        return
    order_id = int(callback.data.split(":")[-1])
    delivery_users = await db.list_users(role="delivery")
    if not delivery_users:
        await callback.answer("Yetkazuvchilar yo'q! Avval xodim qo'shing.", show_alert=True)
        return
    await callback.message.edit_text(
        f"👤 Buyurtma #{order_id} uchun yetkazuvchini tanlang:",
        reply_markup=assign_delivery_kb(order_id, delivery_users),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:assign_do:"))
async def assign_do(callback: CallbackQuery):
    if not await get_admin(callback):
        return
    parts = callback.data.split(":")
    order_id = int(parts[2])
    delivery_id = int(parts[3])
    await db.assign_order(order_id, delivery_id)
    delivery = await db.get_user(delivery_id)
    name = delivery["full_name"] if delivery else str(delivery_id)
    await callback.message.edit_text(
        f"✅ Buyurtma #{order_id} → {name} ga tayinlandi."
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:delete:"))
async def delete_confirm(callback: CallbackQuery):
    if not await get_admin(callback):
        return
    order_id = int(callback.data.split(":")[-1])
    await callback.message.edit_text(
        f"🗑 Buyurtma #{order_id} ni o'chirishni tasdiqlaysizmi?",
        reply_markup=delete_confirm_kb(order_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:delete_yes:"))
async def delete_yes(callback: CallbackQuery):
    if not await get_admin(callback):
        return
    order_id = int(callback.data.split(":")[-1])
    await db.delete_order(order_id)
    await callback.message.edit_text(f"✅ Buyurtma #{order_id} o'chirildi.")
    await callback.answer()
