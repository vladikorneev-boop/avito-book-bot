from flask import Flask
import os
import threading
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ===== ХЕЛС-ЧЕКИ ДЛЯ RENDER =====
@app.route('/')
def index():
    return "✅ Bot is running!", 200

@app.route('/health')
def health():
    return "OK", 200

# ===== ЗАПУСК БОТА =====
def run_bot():
    try:
        # Импортируем только когда нужно
        from bot import dp
        from aiogram import executor
        
        logger.info("🚀 Запуск бота...")
        executor.start_polling(dp, skip_updates=True)
    except Exception as e:
        logger.error(f"❌ Ошибка бота: {e}")

# Запуск бота в фоновом потоке
def start_bot():
    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()
    logger.info("✅ Поток бота запущен")

# Запускаем бота при старте Flask
start_bot()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🔥 Flask сервер запущен на порту {port}")
    app.run(host="0.0.0.0", port=port)