import asyncio
import logging
from datetime import datetime, time, date
from telegram.ext import ContextTypes
import database as db
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def send_reminder(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Отправляет напоминание пользователю"""
    try:
        stats = db.get_user_stats(user_id)
        total = stats['total']
        progress = stats['progress_percent']
        avg_per_day = stats['avg_per_day']
        
        # Рассчитываем сколько нужно сделать сегодня для достижения цели
        today = date.today()
        days_passed = max(1, (today - config.CHALLENGE_START_DATE).days + 1)
        days_remaining = (config.CHALLENGE_END_DATE - today).days
        
        if days_remaining > 0:
            needed_per_day = (config.CHALLENGE_TARGET - total) / days_remaining
        else:
            needed_per_day = 0
        
        reminder_text = (
            f"⏰ Напоминание о челлендже подтягиваний! 💪\n\n"
            f"📊 Твой прогресс:\n"
            f"🎯 Всего: {total:,} подтягиваний\n"
            f"✅ Прогресс: {progress:.1f}%\n"
            f"📈 Среднее в день: {avg_per_day}\n\n"
        )
        
        if days_remaining > 0 and needed_per_day > 0:
            reminder_text += (
                f"📅 Осталось дней: {days_remaining}\n"
                f"🎯 Нужно в день для цели: {needed_per_day:.1f}\n\n"
            )
        
        reminder_text += "Не забудь записать свои подтягивания сегодня! 💪"
        
        await context.bot.send_message(chat_id=user_id, text=reminder_text)
        logger.info(f"Напоминание отправлено пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")


async def daily_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Ежедневная задача для отправки напоминаний всем пользователям"""
    try:
        users = db.get_all_users()
        logger.info(f"Отправка напоминаний {len(users)} пользователям")
        
        for user_id in users:
            await send_reminder(context, user_id)
            # Небольшая задержка между отправками, чтобы не превысить лимиты API
            await asyncio.sleep(0.1)
            
    except Exception as e:
        logger.error(f"Ошибка при отправке ежедневных напоминаний: {e}")


def setup_reminders(application):
    """Настраивает расписание напоминаний"""
    # Парсим время напоминания
    try:
        hour, minute = map(int, config.REMINDER_TIME.split(':'))
        reminder_time = time(hour, minute)
    except:
        logger.warning(f"Неверный формат времени напоминания: {config.REMINDER_TIME}, используем 09:00")
        reminder_time = time(9, 0)
    
    # Добавляем задачу на ежедневное напоминание
    job_queue = application.job_queue
    
    if job_queue:
        job_queue.run_daily(
            daily_reminder,
            time=reminder_time,
            name="daily_reminder"
        )
        logger.info(f"Напоминания настроены на {reminder_time.strftime('%H:%M')} UTC")
    else:
        logger.warning("Job queue не доступен, напоминания не будут работать")

