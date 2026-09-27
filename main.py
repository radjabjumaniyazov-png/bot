import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

# ----------------------------------------------------
# НАСТРОЙКИ
# ----------------------------------------------------
BOT_TOKEN = "8835043120:AAGSU7ZPkm2e30xMoZ1am-zE5qv9EXnwUGk"
ADMIN_ID = int(os.getenv("ADMIN_ID", 8099579471))
CHANNEL_ID = "@ResaleFlowersru"
BOT_USERNAME = "ResaleFlowers_ru_bot"
PAYMENT_REQUISITES = "Карта: 2202 2083 6481 5424 (Получатель: Адиля Закровна)"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Временная база данных в памяти (Рекомендуется заменить на SQLite / PostgreSQL)
users_db = {}  # user_id -> phone
posts_db = {}  # post_id -> data
post_counter = 1


# ----------------------------------------------------
# СОСТОЯНИЯ (FSM)
# ----------------------------------------------------
class SellFlower(StatesGroup):
    photo = State()
    category = State()
    size = State()
    condition = State()
    city = State()
    description = State()
    price = State()
    preview = State()
    payment_check = State()


class RejectReason(StatesGroup):
    waiting_for_reason = State()


# ----------------------------------------------------
# КЛАВИАТУРЫ
# ----------------------------------------------------
def main_menu_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💐 Продать букет", callback_data="sell_flower")],
            [InlineKeyboardButton(text="🔨 Выставить букет на аукцион", callback_data="auction")],
        ]
    )


def contact_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def categories_kb():
    buttons = [
        [
            InlineKeyboardButton(text="Розы 🌹", callback_data="cat_Розы"),
            InlineKeyboardButton(text="Лилии 🪷", callback_data="cat_Лилии"),
        ],
        [
            InlineKeyboardButton(text="Тюльпаны 🌷", callback_data="cat_Тюльпаны"),
            InlineKeyboardButton(text="Пионы 🌸", callback_data="cat_Пионы"),
        ],
        [
            InlineKeyboardButton(text="Хризантемы 🌼", callback_data="cat_Хризантемы"),
            InlineKeyboardButton(text="Сборный букет 💐", callback_data="cat_Сборный букет"),
        ],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def sizes_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Маленький", callback_data="size_Маленький"),
                InlineKeyboardButton(text="Средний", callback_data="size_Средний"),
                InlineKeyboardButton(text="Большой", callback_data="size_Большой"),
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_cat")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        ]
    )


def conditions_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Наисвежайшие ✨", callback_data="cond_Наисвежайшие")],
            [InlineKeyboardButton(text="Свежие 👍", callback_data="cond_Свежие")],
            [InlineKeyboardButton(text="Удовлетворительное 👌", callback_data="cond_Удовлетворительное")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_size")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        ]
    )


def cities_kb():
    cities = ["Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань", "Краснодар"]
    buttons = [[InlineKeyboardButton(text=city, callback_data=f"city_{city}")] for city in cities]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_cond")])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def nav_kb(back_callback: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback)],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        ]
    )


def preview_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Опубликовать", callback_data="publish")],
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data="sell_flower")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        ]
    )


# ----------------------------------------------------
# ОБРАБОТЧИКИ КОМАНД И СТАРТА
# ----------------------------------------------------
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id

    # Проверка на глубокую ссылку покупки из канала
    if message.text and len(message.text.split()) > 1 and message.text.split()[1].startswith("buy_"):
        await process_buy_deep_link(message)
        return

    start_text = (
        "🌸 <b>Добро пожаловать в ResaleFlowers!</b>\n\n"
        "Здесь вы можете быстро продать или приобрести свежие букеты цветов напрямую от флористов и владельцев.\n\n"
        "Для продолжения работы, пожалуйста, поделитесь вашим контактом."
    )

    if user_id in users_db:
        await message.answer("Главное меню:", reply_markup=main_menu_kb())
    else:
        await message.answer(start_text, reply_markup=contact_kb(), parse_mode=ParseMode.HTML)


@dp.message(F.contact)
async def process_contact(message: Message):
    users_db[message.from_user.id] = message.contact.phone_number
    await message.answer(
        "✅ Спасибо! Ваш номер успешно сохранен.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer("Выберите действие:", reply_markup=main_menu_kb())


@dp.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu_kb())


@dp.callback_query(F.data == "auction")
async def process_auction(callback: CallbackQuery):
    await callback.answer("Раздел 'Аукцион' находится в разработке.", show_alert=True)


# ----------------------------------------------------
# СЦЕНАРИЙ: ПРОДАЖА БУКЕТА (FSM)
# ----------------------------------------------------
@dp.callback_query(F.data == "sell_flower")
async def start_sell(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SellFlower.photo)
    await callback.message.answer(
        "📸 Пожалуйста, отправьте фото вашего букета:",
        reply_markup=nav_kb("main_menu"),
    )


@dp.message(SellFlower.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo=photo_id)
    await state.set_state(SellFlower.category)
    await message.answer("💐 Выберите категорию цветов:", reply_markup=categories_kb())


@dp.callback_query(SellFlower.category, F.data.startswith("cat_"))
async def process_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("cat_")[1]
    await state.update_data(category=category)
    await state.set_state(SellFlower.size)
    await callback.message.edit_text("📏 Выберите размер букета:", reply_markup=sizes_kb())


@dp.callback_query(F.data == "back_to_cat")
async def back_to_category(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SellFlower.category)
    await callback.message.edit_text("💐 Выберите категорию цветов:", reply_markup=categories_kb())


@dp.callback_query(SellFlower.size, F.data.startswith("size_"))
async def process_size(callback: CallbackQuery, state: FSMContext):
    size = callback.data.split("size_")[1]
    await state.update_data(size=size)
    await state.set_state(SellFlower.condition)
    await callback.message.edit_text("✨ Укажите состояние цветов:", reply_markup=conditions_kb())


@dp.callback_query(F.data == "back_to_size")
async def back_to_size(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SellFlower.size)
    await callback.message.edit_text("📏 Выберите размер букета:", reply_markup=sizes_kb())


@dp.callback_query(SellFlower.condition, F.data.startswith("cond_"))
async def process_condition(callback: CallbackQuery, state: FSMContext):
    condition = callback.data.split("cond_")[1]
    await state.update_data(condition=condition)
    await state.set_state(SellFlower.city)
    await callback.message.edit_text("🏙 Выберите ваш город:", reply_markup=cities_kb())


@dp.callback_query(F.data == "back_to_cond")
async def back_to_condition(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SellFlower.condition)
    await callback.message.edit_text("✨ Укажите состояние цветов:", reply_markup=conditions_kb())


@dp.callback_query(SellFlower.city, F.data.startswith("city_"))
async def process_city(callback: CallbackQuery, state: FSMContext):
    city = callback.data.split("city_")[1]
    await state.update_data(city=city)
    await state.set_state(SellFlower.description)
    await callback.message.answer(
        "📝 Напишите краткое описание вашего букета (состав, упаковочные материалы, особые примечания):",
        reply_markup=nav_kb("back_to_cond"),
    )


@dp.message(SellFlower.description, F.text)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(SellFlower.price)
    await message.answer(
        "💰 Укажите стоимость букета в рублях (только число, например: 2500):",
        reply_markup=nav_kb("main_menu"),
    )


@dp.message(SellFlower.price, F.text)
async def process_price(message: Message, state: FSMContext):
    clean_price = message.text.replace(" ", "")
    if not clean_price.isdigit():
        await message.answer("⚠️ Пожалуйста, введите цену только цифрами (например, 2500):")
        return

    await state.update_data(price=int(clean_price))
    data = await state.get_data()

    preview_text = (
        f"🔍 <b>Предпросмотр вашего объявления:</b>\n\n"
        f"💐 Категория: {data['category']}\n"
        f"📏 Размер: {data['size']}\n"
        f"✨ Состояние: {data['condition']}\n"
        f"🏙 Город: {data['city']}\n"
        f"📝 Описание: {data['description']}\n"
        f"💰 Цена: {data['price']} руб."
    )

    await state.set_state(SellFlower.preview)
    await message.answer_photo(
        photo=data["photo"],
        caption=preview_text,
        reply_markup=preview_kb(),
        parse_mode=ParseMode.HTML,
    )


@dp.callback_query(SellFlower.preview, F.data == "publish")
async def process_publish(callback: CallbackQuery):
    info_text = (
        "📢 <b>Публикация объявления стоит 99 рублей.</b>\n\n"
        "Эта символическая плата помогает нам защитить канал от спама и поддерживать высокое качество объявлений.\n\n"
        "После оплаты объявление отправится на быструю проверку модератору."
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить 99 руб.", callback_data="pay_start")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        ]
    )
    await callback.message.answer(info_text, reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "pay_start")
async def process_pay_start(callback: CallbackQuery, state: FSMContext):
    pay_text = (
        f"💳 <b>Реквизиты для оплаты:</b>\n{PAYMENT_REQUISITES}\n\n"
        f"Сумма к оплате: <b>99 руб.</b>\n\n"
        f"После перевода отправьте сюда фотографию/скриншот чека оплаты."
    )
    await state.set_state(SellFlower.payment_check)
    await callback.message.answer(pay_text, parse_mode=ParseMode.HTML)


@dp.message(SellFlower.payment_check, F.photo)
async def process_check(message: Message, state: FSMContext):
    global post_counter
    data = await state.get_data()
    post_id = post_counter
    post_counter += 1

    # Сохраняем пост
    posts_db[post_id] = {
        "seller_id": message.from_user.id,
        "seller_username": message.from_user.username,
        "seller_phone": users_db.get(message.from_user.id, "Не указан"),
        "data": data,
        "status": "moderation",
    }

    await message.answer(
        "⏳ Чек принят! Ваше объявление отправлено модератору на проверку. Мы уведомим вас о решении."
    )
    await state.clear()

    # Клавиатура модератора
    admin_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_{post_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{post_id}"),
            ]
        ]
    )

    caption = (
        f"🆕 <b>Новое объявление на проверку #{post_id}</b>\n\n"
        f"Продавец: @{message.from_user.username or 'нет_юзернейма'} (ID: {message.from_user.id})\n"
        f"Тел: {users_db.get(message.from_user.id, 'Не указан')}\n\n"
        f"💐 Категория: {data['category']}\n"
        f"📏 Размер: {data['size']}\n"
        f"✨ Состояние: {data['condition']}\n"
        f"🏙 Город: {data['city']}\n"
        f"📝 Описание: {data['description']}\n"
        f"💰 Цена: {data['price']} руб."
    )

    # Отправляем админу чек и объявление
    await bot.send_photo(
        ADMIN_ID,
        photo=message.photo[-1].file_id,
        caption=f"🧾 Чек к объявлению #{post_id}",
    )
    await bot.send_photo(
        ADMIN_ID, photo=data["photo"], caption=caption, reply_markup=admin_kb, parse_mode=ParseMode.HTML
    )


# ----------------------------------------------------
# ДЕЙСТВИЯ МОДЕРАТОРА И ПУБЛИКАЦИЯ В КАНАЛ
# ----------------------------------------------------
@dp.callback_query(F.data.startswith("approve_"))
async def approve_post(callback: CallbackQuery):
    post_id = int(callback.data.split("_")[1])
    post = posts_db.get(post_id)

    if not post:
        await callback.answer("Объявление не найдено.")
        return

    data = post["data"]

    channel_text = (
        f"💐 <b>В ПРОДАЖЕ</b>\n\n"
        f"🌸 {data['category']} ({data['size']})\n"
        f"✨ Состояние: {data['condition']}\n"
        f"🏙 Город: {data['city']}\n\n"
        f"📝 {data['description']}\n\n"
        f"💰 Цена: {data['price']} руб."
    )

    buy_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛍 Перейти к покупке",
                    url=f"https://t.me/{BOT_USERNAME}?start=buy_{post_id}",
                )
            ]
        ]
    )

    # Публикация в канал
    msg = await bot.send_photo(
        CHANNEL_ID, photo=data["photo"], caption=channel_text, reply_markup=buy_kb, parse_mode=ParseMode.HTML
    )
    posts_db[post_id]["channel_message_id"] = msg.message_id
    posts_db[post_id]["status"] = "active"

    # Уведомление продавцу
    seller_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔴 Отметить как ПРОДАНО", callback_data=f"sold_{post_id}")]
        ]
    )
    await bot.send_message(
        post["seller_id"],
        f"🎉 Ваше объявление #{post_id} успешно прошло модерацию и опубликовано в канале!",
        reply_markup=seller_kb,
    )
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ <b>ОДОБРЕНО</b>", parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data.startswith("reject_"))
async def reject_post(callback: CallbackQuery, state: FSMContext):  # ИСПРАВЛЕНО: Добавлен state
    post_id = int(callback.data.split("_")[1])
    await state.update_data(reject_post_id=post_id)
    await state.set_state(RejectReason.waiting_for_reason)
    await callback.message.answer(
        "Напишите причину отклонения объявления (она будет отправлена продавцу):"
    )


@dp.message(RejectReason.waiting_for_reason)
async def process_reject_reason(message: Message, state: FSMContext):
    fsm_data = await state.get_data()
    post_id = fsm_data["reject_post_id"]
    post = posts_db.get(post_id)

    if post:
        await bot.send_message(
            post["seller_id"],
            f"❌ Ваше объявление #{post_id} отклонено модератором.\n\n<b>Причина:</b> {message.text}",
            parse_mode=ParseMode.HTML,
        )
    await message.answer("Причина отправлена продавцу.")
    await state.clear()


# ----------------------------------------------------
# ПОКУПКА БУКЕТА (ДЛЯ ПОКУПАТЕЛЯ)
# ----------------------------------------------------
async def process_buy_deep_link(message: Message):
    post_id = int(message.text.split("buy_")[1])
    post = posts_db.get(post_id)

    if not post or post["status"] != "active":
        await message.answer("К сожалению, это объявление больше недоступно.")
        return

    data = post["data"]
    safety_text = (
        "🛡 <b>Безопасная сделка & Рекомендации:</b>\n\n"
        "Во избежание мошенничества настоятельно рекомендуем проверять качество букета "
        "и соответствие фото лично при получении/доставке перед передачей денежных средств.\n\n"
    )

    info_text = (
        f"{safety_text}"
        f"🌸 <b>{data['category']}</b> ({data['size']})\n"
        f"🏙 Город: {data['city']}\n"
        f"💰 Цена: {data['price']} руб."
    )

    buy_confirm_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📞 Связаться с продавцом",
                    callback_data=f"confirm_buy_{post_id}",
                )
            ]
        ]
    )

    await message.answer_photo(
        photo=data["photo"], caption=info_text, reply_markup=buy_confirm_kb, parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data.startswith("confirm_buy_"))
async def process_confirm_buy(callback: CallbackQuery):
    post_id = int(callback.data.split("_")[2])
    post = posts_db.get(post_id)

    if not post:
        await callback.answer("Объявление не найдено.")
        return

    buyer = callback.from_user
    buyer_phone = users_db.get(buyer.id, "Не указан")
    buyer_username = f"@{buyer.username}" if buyer.username else "без юзернейма"

    seller_text = (
        f"🔔 <b>У вас новый покупатель на объявление #{post_id}!</b>\n\n"
        f"Покупатель: {buyer_username} (Имя: {buyer.full_name})\n"
        f"Телефон: {buyer_phone}\n\n"
        f"Свяжитесь с покупателем для уточнения деталей доставки."
    )

    await bot.send_message(post["seller_id"], seller_text, parse_mode=ParseMode.HTML)

    await callback.message.answer(
        "📩 Ваши контакты отправлены продавцу! Он свяжется с вами в ближайшее время."
    )
    await callback.answer()


# ----------------------------------------------------
# ОБНОВЛЕНИЕ СТАТУСА НА "ПРОДАНО"
# ----------------------------------------------------
@dp.callback_query(F.data.startswith("sold_"))
async def process_sold(callback: CallbackQuery):
    post_id = int(callback.data.split("_")[1])
    post = posts_db.get(post_id)

    if not post:
        await callback.answer("Объявление не найдено.")
        return

    post["status"] = "sold"
    data = post["data"]

    sold_channel_text = (
        f"🔴 <b>ПРОДАНО</b>\n\n"
        f"🌸 {data['category']} ({data['size']})\n"
        f"🏙 Город: {data['city']}\n"
        f"💰 Цена: {data['price']} руб.\n\n"
        f"Товар более недоступен."
    )

    try:
        await bot.edit_message_caption(
            chat_id=CHANNEL_ID,
            message_id=post["channel_message_id"],
            caption=sold_channel_text,
            reply_markup=None,
            parse_mode=ParseMode.HTML,
        )
        await callback.message.edit_text("✅ Статус объявления в канале изменен на ПРОДАНО.")
    except Exception as e:
        await callback.message.answer(f"Статус обновлен в базе. (Ошибка обновления в канале: {e})")


# ----------------------------------------------------
# ЗАПУСК БОТА
# ----------------------------------------------------
import os
from aiohttp import web

# Простейший веб-сервер для Render, чтобы он видел открытый порт
async def handle(request):
    return web.Response(text="Bot is running!")

app = web.Application()
app.router.add_get("/", handle)

async def web_server():
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# --- ЗАПУСК БОТА И СЕРВЕРА ПАРАЛЛЕЛЬНО ---
async def main():
    # Запускаем polling бота и веб-сервер одновременно
    await asyncio.gather(
        web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
