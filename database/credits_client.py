import sqlite3
import datetime
import pytz
import logging
import os

logger = logging.getLogger(__name__)

# Ścieżka do pliku bazy danych
DB_PATH = "bot_database.sqlite"

def get_user_credits(user_id):
    """
    Pobiera liczbę kredytów użytkownika
    
    Args:
        user_id (int): ID użytkownika
    
    Returns:
        int: Liczba kredytów lub 0, jeśli nie znaleziono
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT credits_amount FROM user_credits WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        
        # Jeśli nie znaleziono, dodaj wpis z 0 kredytów
        add_user_credits(user_id, 0)
        return 0
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu kredytów użytkownika: {e}")
        if 'conn' in locals():
            conn.close()
        return 0

def add_user_credits(user_id, amount, description=None):
    """
    Dodaje kredyty do konta użytkownika
    
    Args:
        user_id (int): ID użytkownika
        amount (int): Liczba kredytów do dodania
        description (str, optional): Opis transakcji
    
    Returns:
        bool: True jeśli operacja się powiodła, False w przeciwnym razie
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Pobierz aktualną liczbę kredytów
        cursor.execute("SELECT credits_amount FROM user_credits WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        
        now = datetime.datetime.now(pytz.UTC).isoformat()
        
        if result:
            current_credits = result[0]
            # Aktualizuj istniejący rekord
            cursor.execute(
                "UPDATE user_credits SET credits_amount = credits_amount + ?, total_credits_purchased = total_credits_purchased + ? WHERE user_id = ?",
                (amount, amount, user_id)
            )
        else:
            # Utwórz nowy rekord
            current_credits = 0
            cursor.execute(
                "INSERT INTO user_credits (user_id, credits_amount, total_credits_purchased, last_purchase_date) VALUES (?, ?, ?, ?)",
                (user_id, amount, amount, now)
            )
        
        # Zapisz transakcję
        if amount != 0:  # Nie zapisujemy transakcji inicjalizujących z 0 kredytów
            cursor.execute(
                "INSERT INTO credit_transactions (user_id, transaction_type, amount, credits_before, credits_after, description, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, "add", amount, current_credits, current_credits + amount, description, now)
            )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Błąd przy dodawaniu kredytów użytkownika: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def deduct_user_credits(user_id, amount, description=None):
    """
    Odejmuje kredyty z konta użytkownika
    
    Args:
        user_id (int): ID użytkownika
        amount (int): Liczba kredytów do odjęcia
        description (str, optional): Opis transakcji
    
    Returns:
        bool: True jeśli operacja się powiodła, False w przeciwnym razie
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Pobierz aktualną liczbę kredytów
        cursor.execute("SELECT credits_amount FROM user_credits WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            # Użytkownik nie ma rekordu w tabeli
            conn.close()
            return False
        
        current_credits = result[0]
        
        # Sprawdź, czy użytkownik ma wystarczającą liczbę kredytów
        if current_credits < amount:
            conn.close()
            return False
        
        # Odejmij kredyty
        cursor.execute(
            "UPDATE user_credits SET credits_amount = credits_amount - ? WHERE user_id = ?",
            (amount, user_id)
        )
        
        # Zapisz transakcję
        now = datetime.datetime.now(pytz.UTC).isoformat()
        cursor.execute(
            "INSERT INTO credit_transactions (user_id, transaction_type, amount, credits_before, credits_after, description, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, "deduct", amount, current_credits, current_credits - amount, description, now)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Błąd przy odejmowaniu kredytów użytkownika: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def check_user_credits(user_id, amount_needed):
    """
    Sprawdza, czy użytkownik ma wystarczającą liczbę kredytów
    
    Args:
        user_id (int): ID użytkownika
        amount_needed (int): Wymagana liczba kredytów
    
    Returns:
        bool: True jeśli użytkownik ma wystarczającą liczbę kredytów, False w przeciwnym razie
    """
    try:
        current_credits = get_user_credits(user_id)
        return current_credits >= amount_needed
    except Exception as e:
        logger.error(f"Błąd przy sprawdzaniu kredytów użytkownika: {e}")
        return False

def get_credit_packages():
    """
    Pobiera dostępne pakiety kredytów
    
    Returns:
        list: Lista słowników z informacjami o pakietach lub pusta lista w przypadku błędu
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, credits, price FROM credit_packages WHERE is_active = 1 ORDER BY credits ASC")
        packages = cursor.fetchall()
        conn.close()
        
        result = []
        for pkg in packages:
            result.append({
                'id': pkg[0],
                'name': pkg[1],
                'credits': pkg[2],
                'price': pkg[3]
            })
        
        return result
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu pakietów kredytów: {e}")
        if 'conn' in locals():
            conn.close()
        return []

def get_package_by_id(package_id):
    """
    Pobiera informacje o pakiecie kredytów
    
    Args:
        package_id (int): ID pakietu
    
    Returns:
        dict: Słownik z informacjami o pakiecie lub None w przypadku błędu
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, credits, price FROM credit_packages WHERE id = ? AND is_active = 1", (package_id,))
        package = cursor.fetchone()
        conn.close()
        
        if package:
            return {
                'id': package[0],
                'name': package[1],
                'credits': package[2],
                'price': package[3]
            }
        
        return None
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu pakietu kredytów: {e}")
        if 'conn' in locals():
            conn.close()
        return None

def purchase_credits(user_id, package_id):
    """
    Dokonuje symulowanego zakupu kredytów (bez faktycznej płatności)
    
    Args:
        user_id (int): ID użytkownika
        package_id (int): ID pakietu
    
    Returns:
        tuple: (success, package) gdzie success to bool, a package to słownik z informacjami o pakiecie
    """
    try:
        # Pobierz informacje o pakiecie
        package = get_package_by_id(package_id)
        if not package:
            return False, None
        
        # Dodaj kredyty użytkownikowi
        now = datetime.datetime.now(pytz.UTC).isoformat()
        description = f"Zakup pakietu {package['name']}"
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Aktualizuj informacje o zakupie
        cursor.execute(
            "UPDATE user_credits SET credits_amount = credits_amount + ?, total_credits_purchased = total_credits_purchased + ?, last_purchase_date = ?, total_spent = total_spent + ? WHERE user_id = ?",
            (package['credits'], package['credits'], now, package['price'], user_id)
        )
        
        if cursor.rowcount == 0:
            # Jeśli nie ma rekordu dla użytkownika, utwórz go
            cursor.execute(
                "INSERT INTO user_credits (user_id, credits_amount, total_credits_purchased, last_purchase_date, total_spent) VALUES (?, ?, ?, ?, ?)",
                (user_id, package['credits'], package['credits'], now, package['price'])
            )
        
        # Pobierz aktualną liczbę kredytów po aktualizacji
        cursor.execute("SELECT credits_amount FROM user_credits WHERE user_id = ?", (user_id,))
        current_credits = cursor.fetchone()[0]
        
        # Zapisz transakcję
        cursor.execute(
            "INSERT INTO credit_transactions (user_id, transaction_type, amount, credits_before, credits_after, description, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, "purchase", package['credits'], current_credits - package['credits'], current_credits, description, now)
        )
        
        conn.commit()
        conn.close()
        
        return True, package
    except Exception as e:
        logger.error(f"Błąd przy zakupie kredytów: {e}")
        if 'conn' in locals():
            conn.close()
        return False, None

def get_user_credit_stats(user_id):
    """
    Pobiera statystyki kredytów użytkownika
    
    Args:
        user_id (int): ID użytkownika
    
    Returns:
        dict: Słownik z informacjami o kredytach użytkownika
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT credits_amount, total_credits_purchased, last_purchase_date, total_spent 
            FROM user_credits 
            WHERE user_id = ?
        """, (user_id,))
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return {
                'credits': 0,
                'total_purchased': 0,
                'last_purchase': None,
                'total_spent': 0.0,
                'usage_history': []
            }
        
        # Pobierz historię ostatnich 10 transakcji
        cursor.execute("""
            SELECT transaction_type, amount, credits_after, description, created_at 
            FROM credit_transactions 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 10
        """, (user_id,))
        
        transactions = cursor.fetchall()
        conn.close()
        
        usage_history = []
        for trans in transactions:
            usage_history.append({
                'type': trans[0],
                'amount': trans[1],
                'balance': trans[2],
                'description': trans[3],
                'date': trans[4]
            })
        
        return {
            'credits': result[0],
            'total_purchased': result[1],
            'last_purchase': result[2],
            'total_spent': result[3],
            'usage_history': usage_history
        }
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu statystyk kredytów użytkownika: {e}")
        if 'conn' in locals():
            conn.close()
        return {
            'credits': 0,
            'total_purchased': 0,
            'last_purchase': None,
            'total_spent': 0.0,
            'usage_history': []
        }
        # Dodaj te funkcje do credits_client.py

def add_stars_payment_option(user_id, stars_amount, credits_amount, description=None):
    """
    Dodaje kredyty do konta użytkownika za płatność gwiazdkami
    
    Args:
        user_id (int): ID użytkownika
        stars_amount (int): Liczba gwiazdek
        credits_amount (int): Liczba kredytów do dodania
        description (str, optional): Opis transakcji
    
    Returns:
        bool: True jeśli operacja się powiodła, False w przeciwnym razie
    """
    try:
        # Wykorzystamy istniejącą funkcję add_user_credits
        if description is None:
            description = f"Zakup za {stars_amount} gwiazdek Telegram"
        
        return add_user_credits(user_id, credits_amount, description)
    except Exception as e:
        logger.error(f"Błąd przy dodawaniu kredytów za gwiazdki: {e}")
        return False

def get_stars_conversion_rate():
    """
    Pobiera aktualny kurs wymiany gwiazdek na kredyty
    
    Returns:
        dict: Słownik z kursami wymiany dla różnych ilości gwiazdek
    """
    # Przykładowy kurs: klucz to liczba gwiazdek, wartość to liczba kredytów
    return {
        1: 10,    # 1 gwiazdka = 10 kredytów
        5: 55,    # 5 gwiazdek = 55 kredytów (10% bonus)
        10: 120,  # 10 gwiazdek = 120 kredytów (20% bonus)
        25: 325,  # 25 gwiazdek = 325 kredytów (30% bonus)
        50: 700   # 50 gwiazdek = 700 kredytów (40% bonus)
    }