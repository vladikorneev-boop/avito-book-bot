import os

# Токен берем из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

# ===== НАСТРОЙКИ ПОИСКА =====
DEFAULT_CITY = ""  # пустая строка = вся Россия
DEFAULT_MIN_PRICE = 0
DEFAULT_MAX_PRICE = 1000
DEFAULT_KEYWORDS = "детские книги"
CHECK_INTERVAL_MINUTES = 15
MAX_ITEMS_PER_SEARCH = 20