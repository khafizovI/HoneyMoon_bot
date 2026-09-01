from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def admin_main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Buyurtma qo'shish"), KeyboardButton(text="📋 Buyurtmalar")],
            [KeyboardButton(text="🏭 Ombor"), KeyboardButton(text="📊 Hisobot")],
            [KeyboardButton(text="👥 Xodimlar"), KeyboardButton(text="❓ Yordam")],
        ],
        resize_keyboard=True,
    )


def delivery_main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 Mening buyurtmalarim")],
            [KeyboardButton(text="🆕 Yangi buyurtmalar")],
            [KeyboardButton(text="❓ Yordam")],
        ],
        resize_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
    )


def location_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Lokatsiyani yuborish", request_location=True)],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
    )


def confirm_order_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="order:confirm"),
                InlineKeyboardButton(text="❌ Bekor", callback_data="order:cancel"),
            ]
        ]
    )


def orders_list_kb(orders: list, prefix: str = "order", page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    buttons = []
    for o in orders:
        label = f"#{o['id']} {o['pharmacy_name'][:20]}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"{prefix}:view:{o['id']}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"{prefix}:page:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"{prefix}:page:{page + 1}"))
    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def order_actions_admin_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👤 Yetkazuvchi tayinlash", callback_data=f"admin:assign:{order_id}"),
            ],
            [
                InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"admin:delete:{order_id}"),
                InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:order:page:0"),
            ],
        ]
    )


def assign_delivery_kb(order_id: int, delivery_users: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=f"🚚 {u['full_name']}",
            callback_data=f"admin:assign_do:{order_id}:{u['telegram_id']}",
        )]
        for u in delivery_users
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"admin:order:{order_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def delete_confirm_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"admin:delete_yes:{order_id}"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data=f"admin:order:{order_id}"),
            ]
        ]
    )


def delivery_order_kb(order_id: int, status: str, order: dict | None = None) -> InlineKeyboardMarkup:
    buttons = []
    if order and order.get("latitude") and order.get("longitude"):
        lat, lon = order["latitude"], order["longitude"]
        buttons.append([
            InlineKeyboardButton(
                text="🗺 Xaritada ochish",
                url=f"https://maps.google.com/?q={lat},{lon}",
            )
        ])
    if status in ("assigned", "pending"):
        buttons.append([
            InlineKeyboardButton(text="📤 Ombordan oldim", callback_data=f"del:pickup:{order_id}")
        ])
    if status == "picked_up":
        buttons.append([
            InlineKeyboardButton(text="📸 Yetkazdim — rasm yuborish", callback_data=f"del:photo:{order_id}")
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="del:orders:0")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def users_list_kb(users: list) -> InlineKeyboardMarkup:
    buttons = []
    for u in users:
        role_icon = "👑" if u["role"] == "admin" else "🚚"
        buttons.append([
            InlineKeyboardButton(
                text=f"{role_icon} {u['full_name']} ({u['telegram_id']})",
                callback_data=f"admin:user:{u['telegram_id']}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="➕ Xodim qo'shish", callback_data="admin:add_user"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def user_actions_kb(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"admin:remove_user:{telegram_id}")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:users")],
        ]
    )


def role_select_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👑 Admin", callback_data="role:admin")],
            [InlineKeyboardButton(text="🚚 Yetkazuvchi", callback_data="role:delivery")],
        ]
    )
