import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date, datetime
from config import DATABASE_URL, CHALLENGE_START_DATE, CHALLENGE_END_DATE, CHALLENGE_TARGET
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_connection():
    """Создает подключение к базе данных"""
    try:
        return psycopg2.connect(DATABASE_URL)
    except psycopg2.OperationalError as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка при подключении к БД: {e}")
        raise


def init_database():
    """Инициализирует базу данных, создает таблицы если их нет"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Таблица пользователей
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица подтягиваний
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pullups (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                count INTEGER NOT NULL CHECK (count > 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date DATE DEFAULT CURRENT_DATE
            )
        """)
        
        # Индексы для быстрого поиска
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_pullups_user_id ON pullups(user_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_pullups_date ON pullups(date)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_pullups_user_date ON pullups(user_id, date)
        """)
        
        conn.commit()
        logger.info("База данных инициализирована успешно")
    except Exception as e:
        logger.error(f"Ошибка при инициализации БД: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def add_user(user_id, username=None, first_name=None, last_name=None):
    """Добавляет пользователя в базу данных"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO users (user_id, username, first_name, last_name)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name
        """, (user_id, username, first_name, last_name))
        conn.commit()
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def add_pullups(user_id, count, pullup_date=None):
    """Добавляет подтягивания пользователю"""
    if pullup_date is None:
        pullup_date = date.today()
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO pullups (user_id, count, date)
            VALUES (%s, %s, %s)
        """, (user_id, count, pullup_date))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении подтягиваний: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


def get_user_total(user_id):
    """Возвращает общее количество подтягиваний пользователя"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT COALESCE(SUM(count), 0) as total
            FROM pullups
            WHERE user_id = %s
        """, (user_id,))
        result = cur.fetchone()
        return result[0] if result else 0
    except Exception as e:
        logger.error(f"Ошибка при получении общего количества: {e}")
        return 0
    finally:
        cur.close()
        conn.close()


def get_user_stats(user_id):
    """Возвращает статистику пользователя"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Общее количество
        cur.execute("""
            SELECT COALESCE(SUM(count), 0) as total
            FROM pullups
            WHERE user_id = %s
        """, (user_id,))
        total = cur.fetchone()['total']
        
        # Количество дней с записями
        cur.execute("""
            SELECT COUNT(DISTINCT date) as days_count
            FROM pullups
            WHERE user_id = %s
        """, (user_id,))
        days_count = cur.fetchone()['days_count']
        
        # Среднее в день
        today = date.today()
        days_passed = max(1, (today - CHALLENGE_START_DATE).days + 1)
        avg_per_day = total / days_passed if days_passed > 0 else 0
        
        # Процент выполнения цели
        progress_percent = (total / CHALLENGE_TARGET * 100) if CHALLENGE_TARGET > 0 else 0
        
        # Количество записей
        cur.execute("""
            SELECT COUNT(*) as records_count
            FROM pullups
            WHERE user_id = %s
        """, (user_id,))
        records_count = cur.fetchone()['records_count']
        
        return {
            'total': total,
            'days_count': days_count,
            'avg_per_day': round(avg_per_day, 2),
            'progress_percent': round(progress_percent, 2),
            'records_count': records_count
        }
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        return {
            'total': 0,
            'days_count': 0,
            'avg_per_day': 0,
            'progress_percent': 0,
            'records_count': 0
        }
    finally:
        cur.close()
        conn.close()


def get_leaderboard(limit=20):
    """Возвращает топ пользователей"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT 
                u.user_id,
                u.username,
                u.first_name,
                COALESCE(SUM(p.count), 0) as total
            FROM users u
            LEFT JOIN pullups p ON u.user_id = p.user_id
            GROUP BY u.user_id, u.username, u.first_name
            ORDER BY total DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении лидерборда: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def get_user_rank(user_id):
    """Возвращает позицию пользователя в рейтинге"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            WITH user_totals AS (
                SELECT 
                    u.user_id,
                    COALESCE(SUM(p.count), 0) as total
                FROM users u
                LEFT JOIN pullups p ON u.user_id = p.user_id
                GROUP BY u.user_id
            ),
            ranked_users AS (
                SELECT 
                    user_id,
                    total,
                    ROW_NUMBER() OVER (ORDER BY total DESC) as rank
                FROM user_totals
            )
            SELECT rank
            FROM ranked_users
            WHERE user_id = %s
        """, (user_id,))
        result = cur.fetchone()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Ошибка при получении ранга: {e}")
        return None
    finally:
        cur.close()
        conn.close()


def get_all_users():
    """Возвращает список всех пользователей для напоминаний"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT user_id FROM users")
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"Ошибка при получении списка пользователей: {e}")
        return []
    finally:
        cur.close()
        conn.close()

