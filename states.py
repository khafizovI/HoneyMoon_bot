from aiogram.fsm.state import State, StatesGroup


class AddOrder(StatesGroup):
    pharmacy_name = State()
    location = State()
    quantity = State()
    unit_price = State()
    notes = State()
    confirm = State()


class AddUser(StatesGroup):
    telegram_id = State()
    role = State()


class DeliveryPhoto(StatesGroup):
    waiting_photo = State()
