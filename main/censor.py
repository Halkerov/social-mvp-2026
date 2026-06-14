# Список запрещённых слов (добавляй сюда)
BAD_WORDS = [
    'сука',
    'Блять',
    'Сука',
    'блять',
    # Добавь свои слова
]

def censor_text(text):
    """Заменяет плохие слова на звёздочки"""
    if not text:
        return text
    
    for word in BAD_WORDS:
        text = text.replace(word, '*' * len(word))
        text = text.replace(word.capitalize(), '*' * len(word))
        text = text.replace(word.upper(), '*' * len(word))
    
    return text

def contains_bad_words(text):
    """Проверяет есть ли плохие слова"""
    if not text:
        return False
    
    text_lower = text.lower()
    for word in BAD_WORDS:
        if word in text_lower:
            return True
    return False