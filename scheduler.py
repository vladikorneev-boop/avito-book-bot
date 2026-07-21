from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Scheduler:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.scheduler = AsyncIOScheduler()
        self.running = False
        self.job_func = None
    
    def start(self, interval_minutes, job_func):
        """Запуск планировщика"""
        if not self.running:
            self.job_func = job_func
            
            self.scheduler.add_job(
                job_func,
                trigger=IntervalTrigger(minutes=interval_minutes),
                id='check_books',
                next_run_time=datetime.now()
            )
            
            self.scheduler.start()
            self.running = True
            logger.info(f"✅ Планировщик запущен (интервал: {interval_minutes} мин)")
    
    def stop(self):
        """Остановка планировщика"""
        if self.running:
            self.scheduler.shutdown(wait=False)
            self.running = False
            logger.info("⏹ Планировщик остановлен")