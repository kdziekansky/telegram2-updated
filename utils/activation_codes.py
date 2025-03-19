"""
Moduł do zarządzania kodami aktywacyjnymi
"""
import sqlite3
import random
import string
import datetime
import pytz
import logging

# Ścieżka do pliku bazy danych
DB_PATH = "bot_database.sqlite"

# Konfiguracja loggera
logger = logging.getLogger(__name__)

def generate_activation_code(length=8):
    """
    Generuje unikalny kod aktywacyjny
    
    Args:
        length (int): Długość kodu
        
    Returns:
        str: Wygenerowany kod
    """
    characters = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choice(characters) for _ in range(length))
        
        # Sprawdź, czy kod już istnieje
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT code FROM activation_codes WHERE code = ?", (code,))
        exists = cursor.fetchone()
        conn.close()
        
        if not exists:
            return code

def create_activation_code(credits):
    """
    Tworzy nowy kod aktywacyjny dla określonej liczby kredytów
    
    Args:
        credits (int): Liczba kredytów, które ma dawać kod
        
    Returns:
        str: Utworzony kod aktywacyjny
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        code = generate_activation_code()
        now = datetime.datetime.now(pytz.UTC).isoformat()
        
        cursor.execute(
            "INSERT INTO activation_codes (code, credits, created_at) VALUES (?, ?, ?)",
            (code, credits, now)
        )
        
        conn.commit()
        conn.close()
        
        return code
    except Exception as e:
        logger.error(f"Błąd podczas tworzenia kodu aktywacyjnego: {e}")
        if 'conn' in locals():
            conn.close()
        return None

def create_multiple_codes(credits, count=1):
    """
    Tworzy wiele kodów aktywacyjnych
    
    Args:
        credits (int): Liczba kredytów, które ma dawać każdy kod
        count (int): Liczba kodów do wygenerowania
        
    Returns:
        list: Lista wygenerowanych kodów
    """
    codes = []
    for _ in range(count):
        code = create_activation_code(credits)
        if code:
            codes.append(code)
    
    return codes

def activate_code(user_id, code):
    """
    Aktywuje kod dla użytkownika
    
    Args:
        user_id (int): ID użytkownika
        code (str): Kod aktywacyjny
        
    Returns:
        tuple: (Czy aktywacja się powiodła, liczba kredytów)
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Sprawdź, czy kod istnieje i nie został użyty
        cursor.execute(
            "SELECT id, credits FROM activation_codes WHERE code = ? AND is_used = 0",
            (code,)
        )
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False, 0
        
        code_id, credits = result
        
        # Oznacz kod jako użyty
        now = datetime.datetime.now(pytz.UTC).isoformat()
        cursor.execute(
            "UPDATE activation_codes SET is_used = 1, used_by = ?, used_at = ? WHERE id = ?",
            (user_id, now, code_id)
        )
        
        conn.commit()
        conn.close()
        
        # Dodaj kredyty użytkownikowi
        from database.credits_client import add_user_credits
        add_user_credits(user_id, credits, f"Aktywacja kodu {code}")
        
        return True, credits
    except Exception as e:
        logger.error(f"Błąd podczas aktywacji kodu: {e}")
        if 'conn' in locals():
            conn.close()
        return False, 0

def get_code_info(code):
    """
    Pobiera informacje o kodzie
    
    Args:
        code (str): Kod aktywacyjny
        
    Returns:
        dict: Informacje o kodzie lub None, jeśli kod nie istnieje
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, credits, is_used, used_by, used_at, created_at FROM activation_codes WHERE code = ?",
            (code,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        return {
            'id': result[0],
            'code': code,
            'credits': result[1],
            'is_used': bool(result[2]),
            'used_by': result[3],
            'used_at': result[4],
            'created_at': result[5]
        }
    except Exception as e:
        logger.error(f"Błąd podczas pobierania informacji o kodzie: {e}")
        if 'conn' in locals():
            conn.close()
        return None

def bulk_create_activation_codes(credits_values, count_per_value=10):
    """
    Tworzy wiele kodów aktywacyjnych o różnych wartościach
    
    Args:
        credits_values (list): Lista wartości kredytów
        count_per_value (int): Liczba kodów do wygenerowania dla każdej wartości
        
    Returns:
        dict: Słownik z wygenerowanymi kodami pogrupowanymi według wartości
    """
    result = {}
    
    for credits in credits_values:
        codes = create_multiple_codes(credits, count_per_value)
        result[credits] = codes
    
    return result