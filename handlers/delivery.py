from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from keyboards import delivery_main_kb, orders_list_kb, delivery_order_kb
from states import DeliveryPhoto
from utils import format_order_detail, fmt_datetime

router = Router()
PAGE_SIZE = 8


async def get_delivery(user_id: int) -> dict | None:
    user = await db.get_user(user_id)
    return user if user and user["role"] == "delivery" else None


@router.message(F.text == "📦 Mening buyurtmalarim")
async def my_orders(message: Message):
    if not await get_delivery(message.from_user.id):
        return
    orders = await db.list_orders(assigned_to=message.from_user.id, limit=100)
    my = [o for o in orders if o.get("assigned_to") == message.from_user.id and o["status"] != "delivered"]
    if not my:
        await message.answer("📦 Sizga tayinlangan faol buyurtmalar yo'q.")
        return
    text = f"📦 <b>Mening buyurtmalarim</b> ({len(my)} ta)\n\nTanlang:"
    kb = orders_list_kb(my, prefix="del:order", page=0, total_pages=1)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(F.text == "🆕 Yangi buyurtmalar")
async def new_orders(message: Message):
    if not await get_delivery(message.from_user.id):
        return
    all_orders = await db.list_orders(status="pending", limit=100)
    assigned = await db.list_orders(status="assigned", limit=100)
    available = [o for o in all_orders + assigned if o.get("assigned_to") in (None, message.from_user.id)]
    available = [o for o in available if o["status"] != "delivered"]
    if not available:
        await message.answer("🆕 Yangi buyurtmalar yo'q.")
        return
    text = f"🆕 <b>Mavjud buyurtmalar</b> ({len(available)} ta)\n\nTanlang:"
    kb = orders_list_kb(available, prefix="del:order", page=0, total_pages=1)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("del:orders:"))
async def del_orders_back(callback: CallbackQuery):
    if not await get_delivery(callback.from_user.id):
        return
    orders = await db.list_orders(assigned_to=callback.from_user.id, limit=100)
    my = [o for o in orders if o.get("assigned_to") == callback.from_user.id and o["status"] != "delivered"]
    text = f"📦 <b>Mening buyurtmalarim</b> ({len(my)} ta)"
    kb = orders_list_kb(my, prefix="del:order", page=0, total_pages=1) if my else None
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("del:order:view:"))
async def del_order_view(callback: CallbackQuery):
    if not await get_delivery(callback.from_user.id):
        return
    order_id = int(callback.data.split(":")[-1])
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Topilmadi", show_alert=True)
        return
    text = format_order_detail(order)
    await callback.message.edit_text(
        text,
        reply_markup=delivery_order_kb(order_id, order["status"], order),
        parse_mode="HTML",
    )
    if order.get("latitude") and order.get("longitude"):
        await callback.message.answer_location(
            latitude=order["latitude"],
            longitude=order["longitude"],
        )
    await callback.answer()


@router.callback_query(F.data.startswith("del:pickup:"))
async def del_pickup(callback: CallbackQuery):
    if not await get_delivery(callback.from_user.id):
        return
    order_id = int(callback.data.split(":")[-1])
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Topilmadi", show_alert=True)
        return
    if order.get("assigned_to") is None:
        await db.assign_order(order_id, callback.from_user.id)
    await db.mark_picked_up(order_id)
    order = await db.get_order(order_id)
    await callback.message.edit_text(
        format_order_detail(order) + "\n\n✅ Ombordan olindi!",
        reply_markup=delivery_order_kb(order_id, "picked_up", order),
        parse_mode="HTML",
    )
    await callback.answer("Ombordan olindi! ✅")


@router.callback_query(F.data.startswith("del:photo:"))
async def del_photo_start(callback: CallbackQuery, state: FSMContext):
    if not await get_delivery(callback.from_user.id):
        return
    order_id = int(callback.data.split(":")[-1])
    order = await db.get_order(order_id)
    if not order or order["status"] != "picked_up":
        await callback.answer("Avval ombordan oling!", show_alert=True)
        return
    await state.set_state(DeliveryPhoto.waiting_photo)
    await state.update_data(order_id=order_id)
    await callback.message.answer(
        f"📸 <b>Buyurtma #{order_id}</b> uchun yetkazish rasmini yuboring.\n\n"
        "⚠️ Rasm yuborilgan vaqt avtomatik saqlanadi!",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(DeliveryPhoto.waiting_photo, F.photo)
async def del_photo_received(message: Message, state: FSMContext, bot):
    if not await get_delivery(message.from_user.id):
        return
    data = await state.get_data()
    order_id = data.get("order_id")
    if not order_id:
        await state.clear()
        return

    photo = message.photo[-1]
    await db.mark_delivered(order_id, photo.file_id)
    order = await db.get_order(order_id)

    await state.clear()
    await message.answer(
        f"✅ <b>Buyurtma #{order_id} yetkazildi!</b>\n\n"
        f"📸 <b>Rasm yuklangan vaqt:</b> <b>{fmt_datetime(order['photo_uploaded_at'])}</b>\n\n"
        "Rahmat! 🍯",
        reply_markup=delivery_main_kb(),
        parse_mode="HTML",
    )

    admins = await db.list_users(role="admin")
    notify = (
        f"✅ <b>Yetkazildi — #{order_id}</b>\n"
        f"🏥 {order['pharmacy_name']}\n"
        f"💰 {order['total_price']:,.0f} so'm\n"
        f"📸 <b>Rasm yuklangan:</b> <b>{fmt_datetime(order['photo_uploaded_at'])}</b>"
    ).replace(",", " ")
    for admin in admins:
        try:
            await bot.send_photo(admin["telegram_id"], photo.file_id, caption=notify, parse_mode="HTML")
        except Exception:
            pass


@router.message(DeliveryPhoto.waiting_photo)
async def del_photo_invalid(message: Message):
    await message.answer("❌ Iltimos, rasm (photo) yuboring.")
