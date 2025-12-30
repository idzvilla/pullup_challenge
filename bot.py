import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
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
        f"Используй кнопки ниже для управления своими подтягиваниями!"
    )
    
    keyboard = get_main_keyboard()
    await update.message.reply_text(
        welcome_text,
        reply_markup=keyboard
    )


def get_main_keyboard():
    """Создает главную клавиатуру с кнопками"""
    keyboard = [
        [
            InlineKeyboardButton("➕ Добавить подтягивания", callback_data="add_pullups"),
            InlineKeyboardButton("⚡ +50", callback_data="quick_add_50")
        ],
        [
            InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats"),
            InlineKeyboardButton("🏆 Лидерборд", callback_data="leaderboard")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "add_pullups":
        await query.edit_message_text(
            "Введи количество подтягиваний, которое хочешь добавить:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
            ]])
        )
        context.user_data['waiting_for_count'] = True
        
    elif query.data == "quick_add_50":
        success = db.add_pullups(user_id, 50)
        if success:
            total = db.get_user_total(user_id)
            await query.edit_message_text(
                f"✅ Добавлено 50 подтягиваний!\n\n"
                f"📊 Твой общий результат: {total:,}",
                reply_markup=get_main_keyboard()
            )
        else:
            await query.edit_message_text(
                "❌ Ошибка при добавлении подтягиваний. Попробуй еще раз.",
                reply_markup=get_main_keyboard()
            )
            
    elif query.data == "my_stats":
        stats = db.get_user_stats(user_id)
        total = db.get_user_total(user_id)
        rank = db.get_user_rank(user_id)
        
        stats_text = (
            f"📊 Твоя статистика:\n\n"
            f"🎯 Всего подтягиваний: {stats['total']:,}\n"
            f"📈 Среднее в день: {stats['avg_per_day']}\n"
            f"📅 Дней с записями: {stats['days_count']}\n"
            f"📝 Всего записей: {stats['records_count']}\n"
            f"✅ Прогресс: {stats['progress_percent']:.1f}% ({stats['total']:,} / {config.CHALLENGE_TARGET:,})\n"
        )
        
        if rank:
            stats_text += f"\n🏆 Твоя позиция в рейтинге: #{rank}"
        
        await query.edit_message_text(
            stats_text,
            reply_markup=get_main_keyboard()
        )
        
    elif query.data == "leaderboard":
        leaderboard = db.get_leaderboard(20)
        user_id = query.from_user.id
        user_rank = db.get_user_rank(user_id)
        
        if not leaderboard:
            await query.edit_message_text(
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
        
        if user_rank:
            user_total = db.get_user_total(user_id)
            leaderboard_text += f"\n📍 Твоя позиция: #{user_rank} ({user_total:,} подтягиваний)"
        
        await query.edit_message_text(
            leaderboard_text,
            reply_markup=get_main_keyboard()
        )
        
    elif query.data == "back_to_main":
        await query.edit_message_text(
            "Выбери действие:",
            reply_markup=get_main_keyboard()
        )
        context.user_data['waiting_for_count'] = False


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_id = update.effective_user.id
    
    # Проверяем, ожидаем ли мы ввод количества подтягиваний
    if context.user_data.get('waiting_for_count', False):
        text = update.message.text.strip()
        
        # Проверяем, что это число
        if not text.isdigit():
            await update.message.reply_text(
                "❌ Пожалуйста, введи число (например: 10, 25, 100)",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
                ]])
            )
            return
        
        count = int(text)
        
        if count <= 0:
            await update.message.reply_text(
                "❌ Количество должно быть больше 0",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
                ]])
            )
            return
        
        # Добавляем подтягивания
        success = db.add_pullups(user_id, count)
        
        if success:
            total = db.get_user_total(user_id)
            await update.message.reply_text(
                f"✅ Добавлено {count:,} подтягиваний!\n\n"
                f"📊 Твой общий результат: {total:,}",
                reply_markup=get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка при добавлении подтягиваний. Попробуй еще раз.",
                reply_markup=get_main_keyboard()
            )
        
        context.user_data['waiting_for_count'] = False
    else:
        # Если не ожидаем ввод, показываем главное меню
        await update.message.reply_text(
            "Выбери действие:",
            reply_markup=get_main_keyboard()
        )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /stats"""
    user_id = update.effective_user.id
    stats = db.get_user_stats(user_id)
    total = db.get_user_total(user_id)
    rank = db.get_user_rank(user_id)
    
    stats_text = (
        f"📊 Твоя статистика:\n\n"
        f"🎯 Всего подтягиваний: {stats['total']:,}\n"
        f"📈 Среднее в день: {stats['avg_per_day']}\n"
        f"📅 Дней с записями: {stats['days_count']}\n"
        f"📝 Всего записей: {stats['records_count']}\n"
        f"✅ Прогресс: {stats['progress_percent']:.1f}% ({stats['total']:,} / {config.CHALLENGE_TARGET:,})\n"
    )
    
    if rank:
        stats_text += f"\n🏆 Твоя позиция в рейтинге: #{rank}"
    
    await update.message.reply_text(
        stats_text,
        reply_markup=get_main_keyboard()
    )


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /leaderboard"""
    leaderboard = db.get_leaderboard(20)
    user_id = update.effective_user.id
    user_rank = db.get_user_rank(user_id)
    
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
    
    if user_rank:
        user_total = db.get_user_total(user_id)
        leaderboard_text += f"\n📍 Твоя позиция: #{user_rank} ({user_total:,} подтягиваний)"
    
    await update.message.reply_text(
        leaderboard_text,
        reply_markup=get_main_keyboard()
    )


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
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Настройка напоминаний
    reminders.setup_reminders(application)
    
    # Запуск бота
    logger.info("Бот запущен")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

