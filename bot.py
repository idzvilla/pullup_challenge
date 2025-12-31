import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.error import TimedOut, NetworkError
from datetime import date, datetime
import database as db
import config
import reminders

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    welcome_text = (
        f"Привет, {user.first_name}! 👋\n\n"
        f"Добро пожаловать в челлендж подтягиваний! 💪\n\n"
        f"🎯 Цель: {config.CHALLENGE_TARGET:,} подтягиваний за год\n"
        f"📅 Период: {config.CHALLENGE_START_DATE.strftime('%d.%m.%Y')} - "
        f"{config.CHALLENGE_END_DATE.strftime('%d.%m.%Y')}\n\n"
        f"Просто отправь число, чтобы добавить подтягивания!"
    )
    
    keyboard = get_main_keyboard()
    await update.message.reply_text(
        welcome_text,
        reply_markup=keyboard
    )


def get_main_keyboard():
    """Создает главную клавиатуру с кнопками под полем ввода"""
    keyboard = [
        [
            KeyboardButton("➕ Добавить"),
            KeyboardButton("👤 Мой прогресс")
        ],
        [
            KeyboardButton("🏆 Лидерборд"),
            KeyboardButton("📅 Сегодня")
        ],
        [
            KeyboardButton("📌 Правила"),
            KeyboardButton("↩️ Undo")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def handle_add_pullups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик добавления подтягиваний"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Если это число, добавляем подтягивания
    if text.isdigit():
        count = int(text)
        
        if count <= 0:
            await update.message.reply_text(
                "❌ Количество должно быть больше 0",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Добавляем подтягивания
        success = db.add_pullups(user_id, count)
        
        if success:
            total = db.get_user_total(user_id)
            today = db.get_today_pullups(user_id)
            
            response = (
                f"✅ Добавлено {count} подтягиваний.\n\n"
                f"📅 Сегодня: {today}\n"
                f"📊 Всего: {total:,}"
            )
            
            await update.message.reply_text(
                response,
                reply_markup=get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка при добавлении подтягиваний. Попробуй еще раз.",
                reply_markup=get_main_keyboard()
            )
    else:
        # Если не число, просим ввести число
        await update.message.reply_text(
            "Введи количество подтягиваний (просто число, например: 15, 50, 100)",
            reply_markup=get_main_keyboard()
        )


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "➕ Добавить":
        await update.message.reply_text(
            "Введи количество подтягиваний (просто число, например: 15, 50, 100)",
            reply_markup=get_main_keyboard()
        )
        
    elif text == "👤 Мой прогресс":
        await show_progress(update, user_id)
        
    elif text == "🏆 Лидерборд":
        await show_leaderboard(update, user_id)
        
    elif text == "📅 Сегодня":
        await show_today_stats(update, user_id)
        
    elif text == "📌 Правила":
        await show_rules(update)
        
    elif text == "↩️ Undo":
        await undo_last(update, user_id)
        
    else:
        # Если это не кнопка, пытаемся добавить как число
        await handle_add_pullups(update, context)


async def show_progress(update: Update, user_id: int):
    """Показывает прогресс пользователя"""
    stats = db.get_user_stats(user_id)
    total = stats['total']
    rank = db.get_user_rank(user_id)
    today = date.today()
    days_remaining = (config.CHALLENGE_END_DATE - today).days
    
    # Рассчитываем сколько нужно в день
    remaining = config.CHALLENGE_TARGET - total
    needed_per_day = remaining / days_remaining if days_remaining > 0 else 0
    
    # Проверяем отставание от плана (50 в день)
    target_per_day = 50
    days_passed = max(1, (today - config.CHALLENGE_START_DATE).days + 1)
    expected_total = target_per_day * days_passed
    is_behind = total < expected_total
    
    progress_text = (
        f"👤 Ваш прогресс:\n\n"
        f"📊 Всего: {total:,} подтягиваний\n"
        f"📅 Сегодня: {db.get_today_pullups(user_id)}\n"
        f"📈 Среднее в день: {stats['avg_per_day']}\n"
        f"🎯 Осталось до цели: {remaining:,}\n"
    )
    
    if is_behind:
        progress_text += f"⚠️ Вы отстаете от плана (50/день)\n"
    
    progress_text += f"🏠 Нужно в день до конца года: {needed_per_day:.0f}"
    
    if rank:
        progress_text += f"\n\n🏆 Ваша позиция в рейтинге: #{rank}"
    
    await update.message.reply_text(
        progress_text,
        reply_markup=get_main_keyboard()
    )


async def show_leaderboard(update: Update, user_id: int):
    """Показывает лидерборд"""
    leaderboard = db.get_leaderboard(20)
    
    if not leaderboard:
        await update.message.reply_text(
            "📊 Лидерборд пуст. Будь первым! 💪",
            reply_markup=get_main_keyboard()
        )
        return
    
    leaderboard_text = "🏆 ТОП-20 ЛИДЕРОВ:\n\n"
    
    for idx, user in enumerate(leaderboard, 1):
        name = user['first_name'] or user['username'] or f"User {user['user_id']}"
        total = user['total']
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        leaderboard_text += f"{medal} {name}: {total:,}\n"
    
    user_rank = db.get_user_rank(user_id)
    if user_rank:
        user_total = db.get_user_total(user_id)
        leaderboard_text += f"\n📍 Ваша позиция: #{user_rank} ({user_total:,} подтягиваний)"
    
    await update.message.reply_text(
        leaderboard_text,
        reply_markup=get_main_keyboard()
    )


async def show_today_stats(update: Update, user_id: int):
    """Показывает статистику за сегодня"""
    today_count = db.get_today_pullups(user_id)
    total = db.get_user_total(user_id)
    
    today_text = (
        f"📅 Статистика за сегодня:\n\n"
        f"📅 Сегодня: {today_count}\n"
        f"📊 Всего: {total:,}"
    )
    
    await update.message.reply_text(
        today_text,
        reply_markup=get_main_keyboard()
    )


async def show_rules(update: Update):
    """Показывает правила челленджа"""
    rules_text = (
        f"📌 Правила челленджа:\n\n"
        f"🎯 Цель: {config.CHALLENGE_TARGET:,} подтягиваний за год\n"
        f"📅 Период: {config.CHALLENGE_START_DATE.strftime('%d.%m.%Y')} - "
        f"{config.CHALLENGE_END_DATE.strftime('%d.%m.%Y')}\n\n"
        f"💡 Как использовать:\n"
        f"• Просто отправь число, чтобы добавить подтягивания\n"
        f"• Используй кнопки для навигации\n"
        f"• Следи за своим прогрессом и соревнуйся с другими!\n\n"
        f"💪 Удачи в челлендже!"
    )
    
    await update.message.reply_text(
        rules_text,
        reply_markup=get_main_keyboard()
    )


async def undo_last(update: Update, user_id: int):
    """Отменяет последнее добавление подтягиваний"""
    last_pullup = db.get_last_pullup(user_id)
    
    if not last_pullup:
        await update.message.reply_text(
            "❌ Нет записей для отмены",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Удаляем последнюю запись
    success = db.delete_pullup(last_pullup['id'])
    
    if success:
        total = db.get_user_total(user_id)
        today = db.get_today_pullups(user_id)
        
        response = (
            f"↩️ Отменено добавление {last_pullup['count']} подтягиваний\n\n"
            f"📅 Сегодня: {today}\n"
            f"📊 Всего: {total:,}"
        )
        
        await update.message.reply_text(
            response,
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Ошибка при отмене. Попробуй еще раз.",
            reply_markup=get_main_keyboard()
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех текстовых сообщений"""
    text = update.message.text
    
    # Проверяем, это кнопка или число
    if text in ["➕ Добавить", "👤 Мой прогресс", "🏆 Лидерборд", "📅 Сегодня", "📌 Правила", "↩️ Undo"]:
        await handle_button(update, context)
    else:
        # Пытаемся обработать как число для добавления
        await handle_add_pullups(update, context)


def main():
    """Запуск бота"""
    # Проверка конфигурации
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен! Установите его в переменных окружения.")
        return
    
    if not config.DATABASE_URL:
        logger.error("DATABASE_URL не установлен! Установите его в переменных окружения.")
        return
    
    # Инициализация базы данных
    try:
        db.init_database()
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        return
    
    # Создание приложения
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик ошибок
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        error = context.error
        if isinstance(error, (TimedOut, NetworkError)):
            logger.warning(f"Таймаут или сетевая ошибка: {error}")
        else:
            logger.error(f"Необработанная ошибка: {error}", exc_info=error)
    
    application.add_error_handler(error_handler)
    
    # Настройка напоминаний
    reminders.setup_reminders(application)
    
    # Запуск бота
    logger.info("Бот запущен")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
