"""
Система рангов для челленджа подтягиваний.
Ранги обновляются каждую 1000 подтягиваний.
"""

# Словарь рангов: (минимальное_количество, максимальное_количество): "Название ранга"
RANKS = {
    (0, 999): "Пыль",
    (1000, 1999): "Перхоть",
    (2000, 2999): "Чепуха",
    (3000, 3999): "Терпила",
    (4000, 4999): "Дюдик",
    (5000, 5999): "Боровик",
    (6000, 6999): "Шлепок",
    (7000, 7999): "Тютька",
    (8000, 8999): "Гуманоид",
    (9000, 9999): "Юнец",
    (10000, 10999): "Пумба",
    (11000, 11999): "Активист",
    (12000, 12999): "Чойларик",
    (13000, 13999): "Рахит",
    (14000, 14999): "Девственница",
    (15000, 15999): "Залупачес",
    (16000, 16999): "Выдра",
    (17000, 17999): "Папуас",
    (18000, 18999): "Выживший",
    (19000, float('inf')): "Легенда"
}


def get_rank(total_pullups: int) -> str:
    """
    Возвращает название ранга для заданного количества подтягиваний.
    
    Args:
        total_pullups: Общее количество подтягиваний
        
    Returns:
        Название ранга
    """
    for (min_val, max_val), rank_name in RANKS.items():
        if max_val == float('inf'):
            if total_pullups >= min_val:
                return rank_name
        else:
            if min_val <= total_pullups <= max_val:
                return rank_name
    # Если не найден (не должно произойти), возвращаем последний ранг
    return "Легенда"


def get_rank_info(total_pullups: int) -> dict:
    """
    Возвращает информацию о текущем ранге и следующем ранге.
    
    Args:
        total_pullups: Общее количество подтягиваний
        
    Returns:
        Словарь с ключами:
        - current_rank: текущий ранг
        - next_rank: следующий ранг (или None если максимальный)
        - pullups_to_next: сколько подтягиваний до следующего ранга (или 0 если максимальный)
        - current_rank_min: минимальное количество для текущего ранга
        - current_rank_max: максимальное количество для текущего ранга
    """
    current_rank = get_rank(total_pullups)
    
    # Находим текущий диапазон
    current_min = 0
    current_max = 0
    next_rank = None
    next_rank_min = None
    
    for (min_val, max_val), rank_name in sorted(RANKS.items()):
        # Проверяем попадает ли в текущий диапазон
        in_range = False
        if max_val == float('inf'):
            in_range = total_pullups >= min_val
        else:
            in_range = min_val <= total_pullups <= max_val
        
        if in_range:
            current_min = min_val
            current_max = max_val if max_val != float('inf') else None
            
            # Если это максимальный ранг (с float('inf')), следующего ранга нет
            if max_val == float('inf'):
                next_rank = None
                next_rank_min = None
            else:
                # Ищем следующий ранг
                for (next_min, next_max), next_name in sorted(RANKS.items()):
                    if next_min > max_val:
                        next_rank = next_name
                        next_rank_min = next_min
                        break
            break
    
    # Вычисляем сколько осталось до следующего ранга
    if next_rank_min is not None:
        pullups_to_next = next_rank_min - total_pullups
    else:
        pullups_to_next = 0
    
    return {
        'current_rank': current_rank,
        'next_rank': next_rank,
        'pullups_to_next': pullups_to_next,
        'current_rank_min': current_min,
        'current_rank_max': current_max
    }
