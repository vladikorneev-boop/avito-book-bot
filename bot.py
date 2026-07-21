import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

from config import BOT_TOKEN, ADMIN_IDS, CHECK_INTERVAL_MINUTES
from database import Database
from avito_parser import AvitoParser
from scheduler import Scheduler

# ===== НАСТРОЙКА ЛОГИРОВАНИЯ =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== ИНИЦИАЛИЗАЦИЯ =====
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

db = Database()
scheduler = Scheduler(bot, db)

# =============================================
#  КОМАНДЫ БОТА
# =============================================

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user = db.add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    welcome_text = (
        "📚 <b>Добро пожаловать в бот поиска детских книг на Avito!</b>\n\n"
        "🌍 Я ищу детские книги <b>по всей России</b> и присылаю уведомления о новых объявлениях.\n\n"
        "🔍 <b>Что я умею:</b>\n"
        "• Искать книги по всей России\n"
        "• Фильтровать по цене\n"
        "• Оповещать о новых объявлениях\n"
        "• Настраивать город поиска\n\n"
        "📌 Используйте /settings для настройки\n"
        "📌 Или /search для мгновенного поиска"
    )
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔍 Найти книги", callback_data="search_now"),
        InlineKeyboardButton("⚙️ Настройки", callback_data="settings")
    )
    keyboard.add(
        InlineKeyboardButton("🔔 Включить уведомления", callback_data="enable_notify"),
        InlineKeyboardButton("🔕 Отключить уведомления", callback_data="disable_notify")
    )
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")

@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    help_text = (
        "📖 <b>Помощь по боту</b>\n\n"
        "<b>Доступные команды:</b>\n"
        "/start - Запустить бота\n"
        "/help - Показать эту справку\n"
        "/settings - Настройки поиска\n"
        "/search - Мгновенный поиск книг\n"
        "/stop - Отключить уведомления\n\n"
        "<b>🌍 Города для поиска:</b>\n"
        "Вся Россия (по умолчанию)\n"
        "Москва, Санкт-Петербург, Екатеринбург и другие\n\n"
        "<b>📚 Примеры ключевых слов:</b>\n"
        "детские книги, сказки, энциклопедия, азбука, букварь"
    )
    await message.answer(help_text, parse_mode="HTML")

@dp.message_handler(commands=['settings'])
async def cmd_settings(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала используйте /start")
        return
    
    city_display = "🌍 Вся Россия" if not user.search_city else user.search_city
    
    settings_text = (
        "⚙️ <b>Ваши настройки:</b>\n\n"
        f"🔍 Ключевые слова: <b>{user.search_keywords}</b>\n"
        f"📍 Город: <b>{city_display}</b>\n"
        f"💰 Цена: <b>{user.search_min_price} - {user.search_max_price} ₽</b>\n"
        f"🔔 Уведомления: <b>{'✅ Включены' if user.notify_enabled else '❌ Отключены'}</b>\n"
    )
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📍 Изменить город", callback_data="change_city"),
        InlineKeyboardButton("💰 Изменить цену", callback_data="change_price")
    )
    keyboard.add(
        InlineKeyboardButton("🔍 Изменить ключевые слова", callback_data="change_keywords"),
        InlineKeyboardButton("🔄 Сбросить настройки", callback_data="reset_settings")
    )
    keyboard.add(
        InlineKeyboardButton("🔔 Вкл/Выкл уведомления", callback_data="toggle_notify")
    )
    
    await message.answer(settings_text, reply_markup=keyboard, parse_mode="HTML")

@dp.message_handler(commands=['search'])
async def cmd_search(message: types.Message):
    await message.answer("🔍 <b>Ищу книги...</b>\n\n⏳ Это может занять несколько секунд...", parse_mode="HTML")
    
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала используйте /start")
        return
    
    parser = AvitoParser()
    books = parser.search_books(
        query=user.search_keywords,
        city=user.search_city,
        min_price=user.search_min_price,
        max_price=user.search_max_price,
        limit=10
    )
    
    if not books:
        await message.answer(
            "😕 <b>Книг не найдено</b>\n\n"
            "Попробуйте изменить параметры поиска в /settings\n\n"
            "💡 Советы:\n"
            "• Измените ключевые слова\n"
            "• Увеличьте ценовой диапазон\n"
            "• Попробуйте другой город",
            parse_mode="HTML"
        )
        return
    
    for book in books:
        db.save_book(book)
    
    await send_books_list(message.chat.id, books, "📚 <b>Найденные книги:</b>")

@dp.message_handler(commands=['stop'])
async def cmd_stop(message: types.Message):
    db.update_user_settings(message.from_user.id, notify_enabled=False)
    await message.answer(
        "🔕 <b>Уведомления отключены</b>\n\n"
        "Чтобы включить, используйте /start или настройки",
        parse_mode="HTML"
    )

# =============================================
#  INLINE КНОПКИ
# =============================================

@dp.callback_query_handler(lambda c: c.data == "search_now")
async def callback_search_now(callback: types.CallbackQuery):
    await callback.answer("🔍 Ищу книги...")
    await cmd_search(callback.message)

@dp.callback_query_handler(lambda c: c.data == "settings")
async def callback_settings(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_settings(callback.message)

@dp.callback_query_handler(lambda c: c.data == "enable_notify")
async def callback_enable_notify(callback: types.CallbackQuery):
    db.update_user_settings(callback.from_user.id, notify_enabled=True)
    await callback.answer("✅ Уведомления включены!")
    await callback.message.edit_text(
        "✅ <b>Уведомления включены!</b>\n\n"
        "Я буду присылать вам новые объявления о детских книгах.",
        parse_mode="HTML"
    )

@dp.callback_query_handler(lambda c: c.data == "disable_notify")
async def callback_disable_notify(callback: types.CallbackQuery):
    db.update_user_settings(callback.from_user.id, notify_enabled=False)
    await callback.answer("🔕 Уведомления отключены!")
    await callback.message.edit_text(
        "🔕 <b>Уведомления отключены</b>\n\n"
        "Чтобы включить, используйте /start или настройки.",
        parse_mode="HTML"
    )

@dp.callback_query_handler(lambda c: c.data == "toggle_notify")
async def callback_toggle_notify(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if user:
        new_state = not user.notify_enabled
        db.update_user_settings(callback.from_user.id, notify_enabled=new_state)
        await callback.answer(f"{'✅' if new_state else '❌'} Уведомления {'включены' if new_state else 'отключены'}")
        await cmd_settings(callback.message)

@dp.callback_query_handler(lambda c: c.data == "change_city")
async def callback_change_city(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    cities = [
        ("🌍 Вся Россия", ""),
        ("Москва", "moskva"),
        ("Санкт-Петербург", "spb"),
        ("Екатеринбург", "ekaterinburg"),
        ("Новосибирск", "novosibirsk"),
        ("Казань", "kazan"),
        ("Нижний Новгород", "nizhniy_novgorod"),
        ("Краснодар", "krasnodar"),
        ("Ростов-на-Дону", "rostov_na_donu"),
        ("Воронеж", "voronezh"),
        ("Самара", "samara"),
        ("Челябинск", "chelyabinsk"),
        ("Омск", "omsk"),
        ("Красноярск", "krasnoyarsk"),
        ("Волгоград", "volgograd"),
        ("Пермь", "perm"),
    ]
    
    for name, code in cities:
        keyboard.add(InlineKeyboardButton(name, callback_data=f"set_city_{code}"))
    
    await callback.message.edit_text(
        "📍 <b>Выберите город для поиска:</b>\n\n"
        "🌍 <b>Вся Россия</b> — поиск по всем городам",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.callback_query_handler(lambda c: c.data.startswith("set_city_"))
async def callback_set_city(callback: types.CallbackQuery):
    city = callback.data.replace("set_city_", "")
    db.update_user_settings(callback.from_user.id, search_city=city)
    
    city_display = "🌍 Вся Россия" if not city else city
    await callback.answer(f"✅ Город изменен: {city_display}")
    await cmd_settings(callback.message)

@dp.callback_query_handler(lambda c: c.data == "change_price")
async def callback_change_price(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "💰 <b>Настройка цены</b>\n\n"
        "Отправьте цену в формате:\n"
        "<b>минимальная_максимальная</b>\n"
        "Например: <b>0_500</b> или <b>100_1000</b>\n\n"
        "Или просто <b>максимальную</b> цену\n"
        "Например: <b>500</b>\n\n"
        "Или отправьте <b>0</b> для отключения фильтра",
        parse_mode="HTML"
    )

@dp.callback_query_handler(lambda c: c.data == "change_keywords")
async def callback_change_keywords(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "🔍 <b>Изменить ключевые слова</b>\n\n"
        "Отправьте новые ключевые слова для поиска.\n"
        "Например: <b>детские книги сказки</b>\n\n"
        "Или: <b>энциклопедия для детей</b>",
        parse_mode="HTML"
    )

@dp.callback_query_handler(lambda c: c.data == "reset_settings")
async def callback_reset_settings(callback: types.CallbackQuery):
    from config import DEFAULT_CITY, DEFAULT_MIN_PRICE, DEFAULT_MAX_PRICE, DEFAULT_KEYWORDS
    
    db.update_user_settings(
        callback.from_user.id,
        search_city=DEFAULT_CITY,
        search_min_price=DEFAULT_MIN_PRICE,
        search_max_price=DEFAULT_MAX_PRICE,
        search_keywords=DEFAULT_KEYWORDS
    )
    await callback.answer("✅ Настройки сброшены!")
    await cmd_settings(callback.message)

# =============================================
#  ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ
# =============================================

@dp.message_handler(content_types=['text'])
async def handle_text_input(message: types.Message):
    if "_" in message.text and all(c.isdigit() or c == "_" for c in message.text):
        try:
            parts = message.text.split("_")
            if len(parts) == 2:
                min_price = int(parts[0])
                max_price = int(parts[1])
                if min_price >= 0 and max_price > min_price:
                    db.update_user_settings(
                        message.from_user.id,
                        search_min_price=min_price,
                        search_max_price=max_price
                    )
                    await message.answer(f"✅ Цена установлена: {min_price} - {max_price} ₽")
                    await cmd_settings(message)
                    return
        except:
            pass
    
    if message.text.isdigit():
        max_price = int(message.text)
        if max_price > 0:
            db.update_user_settings(
                message.from_user.id,
                search_max_price=max_price,
                search_min_price=0
            )
            await message.answer(f"✅ Цена установлена: 0 - {max_price} ₽")
            await cmd_settings(message)
            return
        elif max_price == 0:
            db.update_user_settings(
                message.from_user.id,
                search_max_price=0,
                search_min_price=0
            )
            await message.answer(f"✅ Фильтр по цене отключен")
            await cmd_settings(message)
            return
    
    if len(message.text) > 2 and not message.text.startswith("/"):
        db.update_user_settings(message.from_user.id, search_keywords=message.text)
        await message.answer(f"✅ Ключевые слова изменены: <b>{message.text}</b>", parse_mode="HTML")
        await cmd_settings(message)
        return
    
    await message.answer(
        "🤖 Я не понял ваш ввод.\n"
        "Используйте /help для списка команд."
    )

# =============================================
#  ФУНКЦИИ ОТПРАВКИ
# =============================================

async def send_books_list(chat_id, books, header="📚 <b>Новые книги:</b>"):
    if not books:
        return
    
    await bot.send_message(chat_id, header, parse_mode="HTML")
    
    for book in books[:10]:
        price_text = f"💰 {int(book['price'])} ₽" if book['price'] > 0 else "💰 Цена не указана"
        
        city_display = "🌍 Вся Россия" if book['city'] == "вся Россия" else book['city']
        
        text = (
            f"<b>{book['title'][:100]}</b>\n\n"
            f"{price_text}\n"
            f"📍 {city_display}\n\n"
        )
        
        if book.get('description'):
            text += f"📖 {book['description'][:200]}...\n\n"
        
        text += f"🔗 <a href='{book['url']}'>Открыть объявление</a>"
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("📱 Открыть в Avito", url=book['url'])
        )
        
        try:
            if book.get('image_url'):
                await bot.send_photo(
                    chat_id,
                    photo=book['image_url'],
                    caption=text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id,
                    text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")
            await bot.send_message(chat_id, text, parse_mode="HTML")
        
        await asyncio.sleep(0.5)

# =============================================
#  УВЕДОМЛЕНИЯ
# =============================================

async def notify_users():
    logger.info("🔄 Проверка новых книг...")
    
    users = db.get_users(active_only=True)
    
    if not users:
        logger.info("👤 Нет активных пользователей")
        return
    
    logger.info(f"👤 Активных пользователей: {len(users)}")
    
    parser = AvitoParser()
    
    for user in users:
        if not user.notify_enabled:
            continue
        
        try:
            books = parser.search_books(
                query=user.search_keywords,
                city=user.search_city,
                min_price=user.search_min_price,
                max_price=user.search_max_price,
                limit=10
            )
            
            new_books = []
            for book in books:
                saved = db.save_book(book)
                if saved:
                    new_books.append(saved)
            
            if new_books:
                logger.info(f"🔔 Найдено {len(new_books)} новых книг для пользователя {user.user_id}")
                
                await send_books_list(
                    user.user_id,
                    new_books,
                    f"🔔 <b>Новые детские книги!</b>\n\n"
                )
                
                db.mark_as_notified([b.id for b in new_books])
            
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ Ошибка для пользователя {user.user_id}: {e}")
    
    logger.info("✅ Проверка завершена")

# =============================================
#  ЗАПУСК
# =============================================

@dp.message_handler()
async def echo(message: types.Message):
    await message.answer(
        "🤖 Я не понял вашу команду.\n"
        "Используйте /help для списка команд."
    )

async def on_startup(dp):
    logger.info("🚀 Бот запущен!")
    scheduler.start(CHECK_INTERVAL_MINUTES, notify_users)
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"✅ <b>Бот запущен!</b>\n"
                f"🌍 Поиск по всей России\n"
                f"🔄 Проверка каждые {CHECK_INTERVAL_MINUTES} минут\n"
                f"👤 Активных пользователей: {len(db.get_users(active_only=True))}",
                parse_mode="HTML"
            )
        except:
            pass

async def on_shutdown(dp):
    logger.info("⏹ Бот останавливается...")
    scheduler.stop()
    await bot.close()

if __name__ == '__main__':
    executor.start_polling(
        dp,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True
    )