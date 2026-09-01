from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message

import database as db
from config import ADMIN_IDS
from keyboards import admin_main_kb, delivery_main_kb

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user and message.from_user.id in ADMIN_IDS:
        await db.add_user(
            message.from_user.id,
            message.from_user.full_name or "Admin",
            message.from_user.username or "",
            "admin",
        )
        user = await db.get_user(message.from_user.id)

    if not user:
        await message.answer(
            "⛔ Sizda botdan foydalanish huquqi yo'q.\n"
            "Admin sizni tizimga qo'shishi kerak."
        )
        return

    if user["role"] == "admin":
        kb = admin_main_kb()
        text = (
            "🍯 <b>Honeymoon.uz — Admin panel</b>\n\n"
            "Buyurtmalar, ombor va hisobotni shu yerdan boshqaring.\n"
            "Quyidagi tugmalardan foydalaning 👇"
        )
    else:
        kb = delivery_main_kb()
        text = (
            "🚚 <b>Honeymoon.uz — Yetkazuvchi panel</b>\n\n"
            "Buyurtmalaringizni ko'ring va yetkazgandan keyin rasm yuboring.\n"
            "Rasm vaqti avtomatik saqlanadi 📸"
        )

    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(F.text == "❓ Yordam")
async def cmd_help(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        return

    if user["role"] == "admin":
        text = (
            "<b>Admin yordam:</b>\n\n"
            "➕ <b>Buyurtma qo'shish</b> — apteka nomi, lokatsiya (xaritadan), miqdor, narx\n"
            "📋 <b>Buyurtmalar</b> — barcha buyurtmalar ro'yxati\n"
            "🏭 <b>Ombor</b> — ombordan olingan/olinmagan + rasm vaqti\n"
            "📊 <b>Hisobot</b> — pul va buyurtmalar statistikasi\n"
            "👥 <b>Xodimlar</b> — yetkazuvchi/admin qo'shish/o'chirish"
        )
    else:
        text = (
            "<b>Yetkazuvchi yordam:</b>\n\n"
            "📦 <b>Mening buyurtmalarim</b> — sizga tayinlangan buyurtmalar\n"
            "🆕 <b>Yangi buyurtmalar</b> — tayinlanmagan buyurtmalar\n\n"
            "1️⃣ Ombordan oldim — tugmasini bosing\n"
            "2️⃣ Yetkazgandan keyin rasm yuboring\n"
            "📸 Rasm yuklangan vaqt avtomatik saqlanadi"
        )
    await message.answer(text, parse_mode="HTML")
