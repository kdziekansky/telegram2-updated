import sqlite3
import uuid
import datetime
import pytz
import json
import logging
import os

logger = logging.getLogger(__name__)

# Ścieżka do pliku bazy danych
DB_PATH = "bot_database.sqlite"

# Inicjalizacja bazy danych SQLite
def init_database():
    """Inicjalizuje bazę danych SQLite i tworzy wymagane tabele"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Tabela users
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT, 
            language_code TEXT,
            subscription_end_date TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            messages_used INTEGER DEFAULT 0,
            messages_limit INTEGER DEFAULT 0
        )
        ''')
        # Tutaj dodaj sprawdzenie i dodanie kolumny language
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        if 'language' not in column_names and 'language_code' in column_names:
            cursor.execute("ALTER TABLE users ADD COLUMN language TEXT")
            cursor.execute("UPDATE users SET language = language_code")
        
        # Tabela licenses
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT UNIQUE,
            duration_days INTEGER NOT NULL,
            message_limit INTEGER DEFAULT 0,
            price REAL NOT NULL,
            is_used INTEGER DEFAULT 0,
            used_at TEXT,
            used_by INTEGER,
            created_at TEXT
        )
        ''')
        
        # Tabela conversations
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            created_at TEXT,
            last_message_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        ''')
        
        # Tabela messages
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            is_from_user INTEGER NOT NULL,
            model_used TEXT,
            created_at TEXT,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        ''')
        
        # Tabela prompt_templates
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS prompt_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            prompt_text TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Baza danych zainicjalizowana pomyślnie")
        return True
    except Exception as e:
        logger.error(f"Błąd inicjalizacji bazy danych SQLite: {e}")
        return False
 
# Inicjalizacja bazy danych przy imporcie modułu
init_database()

def update_user_language(user_id, language):
    """Aktualizuje język użytkownika w bazie danych"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE users SET language = ? WHERE id = ?", (language, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Błąd przy aktualizacji języka użytkownika: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def get_or_create_user(user_id, username=None, first_name=None, last_name=None, language_code=None):
    """Pobierz lub utwórz użytkownika w bazie danych"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Sprawdź czy użytkownik istnieje
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            # Konwertuj krotkę na słownik
            user_dict = {
                'id': user[0],
                'username': user[1],
                'first_name': user[2],
                'last_name': user[3],
                'language_code': user[4],
                'subscription_end_date': user[5],
                'is_active': bool(user[6]),
                'created_at': user[7],
                'messages_used': user[8] if len(user) > 8 else 0,
                'messages_limit': user[9] if len(user) > 9 else 0
            }
            conn.close()
            return user_dict
        
        # Jeśli nie istnieje, utwórz nowego
        now = datetime.datetime.now(pytz.UTC).isoformat()
        cursor.execute(
            "INSERT INTO users (id, username, first_name, last_name, language_code, is_active, created_at, messages_used, messages_limit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, username, first_name, last_name, language_code, 1, now, 0, 0)
        )
        conn.commit()
        
        # Pobierz utworzonego użytkownika
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        new_user = cursor.fetchone()
        conn.close()
        
        if new_user:
            return {
                'id': new_user[0],
                'username': new_user[1],
                'first_name': new_user[2],
                'last_name': new_user[3],
                'language_code': new_user[4],
                'subscription_end_date': new_user[5],
                'is_active': bool(new_user[6]),
                'created_at': new_user[7],
                'messages_used': new_user[8] if len(new_user) > 8 else 0,
                'messages_limit': new_user[9] if len(new_user) > 9 else 0
            }
        
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu/tworzeniu użytkownika: {e}")
        if 'conn' in locals():
            conn.close()
    
    return None

def check_active_subscription(user_id):
    """Sprawdź czy użytkownik ma aktywną subskrypcję czasową lub wiadomości"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Sprawdź subskrypcję czasową
        cursor.execute("SELECT subscription_end_date FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            end_date = datetime.datetime.fromisoformat(result[0].replace('Z', '+00:00'))
            now = datetime.datetime.now(pytz.UTC)
            if end_date > now:
                conn.close()
                return True
        
        # Sprawdź limit wiadomości
        if check_message_limit(user_id):
            conn.close()
            return True
            
        conn.close()
        return False
    except Exception as e:
        logger.error(f"Błąd przy sprawdzaniu subskrypcji: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def get_subscription_end_date(user_id):
    """Pobierz datę końca subskrypcji użytkownika"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT subscription_end_date FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            return None
        
        return datetime.datetime.fromisoformat(result[0].replace('Z', '+00:00'))
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu daty końca subskrypcji: {e}")
        if 'conn' in locals():
            conn.close()
        return None

def create_license(message_limit, price, duration_days=0):
    """Utwórz nową licencję opartą na liczbie wiadomości"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        license_key = str(uuid.uuid4())
        now = datetime.datetime.now(pytz.UTC).isoformat()
        
        cursor.execute(
            "INSERT INTO licenses (license_key, duration_days, message_limit, price, created_at) VALUES (?, ?, ?, ?, ?)",
            (license_key, duration_days, message_limit, price, now)
        )
        
        license_id = cursor.lastrowid
        conn.commit()
        
        # Pobierz utworzoną licencję
        cursor.execute("SELECT * FROM licenses WHERE id = ?", (license_id,))
        license_data = cursor.fetchone()
        conn.close()
        
        if license_data:
            return {
                'id': license_data[0],
                'license_key': license_data[1],
                'duration_days': license_data[2],
                'message_limit': license_data[3],
                'price': license_data[4],
                'is_used': bool(license_data[5]),
                'used_at': license_data[6],
                'used_by': license_data[7],
                'created_at': license_data[8]
            }
    except Exception as e:
        logger.error(f"Błąd przy tworzeniu licencji: {e}")
        if 'conn' in locals():
            conn.close()
    
    return None

def activate_user_license(user_id, license_key):
    """Aktywuj licencję dla użytkownika"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Pobierz licencję
        cursor.execute(
            "SELECT * FROM licenses WHERE license_key = ? AND is_used = 0", 
            (license_key,)
        )
        license_data = cursor.fetchone()
        
        if not license_data:
            conn.close()
            return False, None, 0  # Dodano trzeci parametr dla message_limit
        
        # Pobierz obecny limit wiadomości użytkownika (jeśli istnieje)
        cursor.execute("SELECT messages_limit, messages_used FROM users WHERE id = ?", (user_id,))
        user_messages = cursor.fetchone()
        
        current_limit = user_messages[0] if user_messages and user_messages[0] else 0
        current_used = user_messages[1] if user_messages and user_messages[1] else 0
        
        # Utwórz słownik z danych licencji - przyjmuję, że message_limit jest na pozycji 3
        license_dict = {
            'id': license_data[0],
            'license_key': license_data[1],
            'duration_days': license_data[2],
            'message_limit': license_data[3],
            'price': license_data[4],
            'is_used': bool(license_data[5]),
            'used_at': license_data[6],
            'used_by': license_data[7],
            'created_at': license_data[8]
        }
        
        # Oblicz datę końca subskrypcji jeśli duration_days > 0
        now = datetime.datetime.now(pytz.UTC)
        end_date = None
        if license_dict['duration_days'] > 0:
            end_date = now + datetime.timedelta(days=license_dict['duration_days'])
        
        # Aktualizuj licencję
        cursor.execute(
            "UPDATE licenses SET is_used = 1, used_at = ?, used_by = ? WHERE id = ?",
            (now.isoformat(), user_id, license_dict['id'])
        )
        
        # Aktualizuj limity wiadomości użytkownika - dodaj nowe do istniejących
        new_message_limit = current_limit + license_dict['message_limit']
        
        # Aktualizuj użytkownika
        if end_date:
            cursor.execute(
                "UPDATE users SET subscription_end_date = ?, messages_limit = ? WHERE id = ?",
                (end_date.isoformat(), new_message_limit, user_id)
            )
        else:
            cursor.execute(
                "UPDATE users SET messages_limit = ? WHERE id = ?",
                (new_message_limit, user_id)
            )
        
        conn.commit()
        conn.close()
        
        return True, end_date, license_dict['message_limit']
    except Exception as e:
        logger.error(f"Błąd przy aktywacji licencji: {e}")
        if 'conn' in locals():
            conn.close()
        return False, None, 0

def check_message_limit(user_id):
    """Sprawdź czy użytkownik ma dostępne wiadomości"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT messages_limit, messages_used FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False
        
        message_limit = result[0] or 0
        messages_used = result[1] or 0
        
        return messages_used < message_limit
    except Exception as e:
        logger.error(f"Błąd przy sprawdzaniu limitu wiadomości: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def increment_messages_used(user_id):
    """Zwiększ licznik wykorzystanych wiadomości"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT messages_used FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False
        
        messages_used = result[0] or 0
        messages_used += 1
        
        cursor.execute(
            "UPDATE users SET messages_used = ? WHERE id = ?",
            (messages_used, user_id)
        )
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Błąd przy aktualizacji licznika wiadomości: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def get_message_status(user_id):
    """Pobierz status wiadomości użytkownika"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT messages_limit, messages_used FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return {
                "messages_limit": 0,
                "messages_used": 0,
                "messages_left": 0
            }
        
        messages_limit = result[0] or 0
        messages_used = result[1] or 0
        messages_left = max(0, messages_limit - messages_used)
        
        return {
            "messages_limit": messages_limit,
            "messages_used": messages_used,
            "messages_left": messages_left
        }
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu statusu wiadomości: {e}")
        if 'conn' in locals():
            conn.close()
        return {
            "messages_limit": 0,
            "messages_used": 0,
            "messages_left": 0
        }

def create_new_conversation(user_id):
    """Utwórz nową konwersację dla użytkownika"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.datetime.now(pytz.UTC).isoformat()
        
        cursor.execute(
            "INSERT INTO conversations (user_id, created_at, last_message_at) VALUES (?, ?, ?)",
            (user_id, now, now)
        )
        
        conversation_id = cursor.lastrowid
        conn.commit()
        
        # Pobierz utworzoną konwersację
        cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        conversation_data = cursor.fetchone()
        conn.close()
        
        if conversation_data:
            return {
                'id': conversation_data[0],
                'user_id': conversation_data[1],
                'created_at': conversation_data[2],
                'last_message_at': conversation_data[3]
            }
    except Exception as e:
        logger.error(f"Błąd przy tworzeniu nowej konwersacji: {e}")
        if 'conn' in locals():
            conn.close()
    
    return None

def get_active_conversation(user_id):
    """Pobierz aktywną konwersację użytkownika (ostatnią)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM conversations WHERE user_id = ? ORDER BY last_message_at DESC LIMIT 1",
            (user_id,)
        )
        
        conversation_data = cursor.fetchone()
        conn.close()
        
        if conversation_data:
            return {
                'id': conversation_data[0],
                'user_id': conversation_data[1],
                'created_at': conversation_data[2],
                'last_message_at': conversation_data[3]
            }
        
        # Jeśli nie ma żadnej konwersacji, utwórz nową
        return create_new_conversation(user_id)
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu aktywnej konwersacji: {e}")
        if 'conn' in locals():
            conn.close()
        return create_new_conversation(user_id)

def save_message(conversation_id, user_id, content, is_from_user, model_used=None):
    """Zapisz wiadomość w bazie danych"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.datetime.now(pytz.UTC).isoformat()
        
        # Zapisz wiadomość
        cursor.execute(
            "INSERT INTO messages (conversation_id, user_id, content, is_from_user, model_used, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (conversation_id, user_id, content, 1 if is_from_user else 0, model_used, now)
        )
        
        # Aktualizuj czas ostatniej wiadomości w konwersacji
        cursor.execute(
            "UPDATE conversations SET last_message_at = ? WHERE id = ?",
            (now, conversation_id)
        )
        
        message_id = cursor.lastrowid
        conn.commit()
        
        # Pobierz zapisaną wiadomość
        cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
        message_data = cursor.fetchone()
        conn.close()
        
        if message_data:
            return {
                'id': message_data[0],
                'conversation_id': message_data[1],
                'user_id': message_data[2],
                'content': message_data[3],
                'is_from_user': bool(message_data[4]),
                'model_used': message_data[5],
                'created_at': message_data[6]
            }
    except Exception as e:
        logger.error(f"Błąd przy zapisywaniu wiadomości: {e}")
        if 'conn' in locals():
            conn.close()
    
    return None

def get_conversation_history(conversation_id, limit=20):
    """Pobierz historię konwersacji"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ?",
            (conversation_id, limit)
        )
        
        messages = cursor.fetchall()
        conn.close()
        
        # Konwertuj na listę słowników
        result = []
        for msg in messages:
            result.append({
                'id': msg[0],
                'conversation_id': msg[1],
                'user_id': msg[2],
                'content': msg[3],
                'is_from_user': bool(msg[4]),
                'model_used': msg[5],
                'created_at': msg[6]
            })
        
        return result
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu historii konwersacji: {e}")
        if 'conn' in locals():
            conn.close()
        return []

def save_prompt_template(name, description, prompt_text):
    """Zapisz szablon prompta w bazie danych"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.datetime.now(pytz.UTC).isoformat()
        
        cursor.execute(
            "INSERT INTO prompt_templates (name, description, prompt_text, is_active, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, description, prompt_text, 1, now)
        )
        
        template_id = cursor.lastrowid
        conn.commit()
        
        # Pobierz zapisany szablon
        cursor.execute("SELECT * FROM prompt_templates WHERE id = ?", (template_id,))
        template_data = cursor.fetchone()
        conn.close()
        
        if template_data:
            return {
                'id': template_data[0],
                'name': template_data[1],
                'description': template_data[2],
                'prompt_text': template_data[3],
                'is_active': bool(template_data[4]),
                'created_at': template_data[5]
            }
    except Exception as e:
        logger.error(f"Błąd przy zapisywaniu szablonu prompta: {e}")
        if 'conn' in locals():
            conn.close()
    
    return None

def get_prompt_templates():
    """Pobierz wszystkie aktywne szablony promptów"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM prompt_templates WHERE is_active = 1")
        
        templates = cursor.fetchall()
        conn.close()
        
        # Konwertuj na listę słowników
        result = []
        for tmpl in templates:
            result.append({
                'id': tmpl[0],
                'name': tmpl[1],
                'description': tmpl[2],
                'prompt_text': tmpl[3],
                'is_active': bool(tmpl[4]),
                'created_at': tmpl[5]
            })
        
        return result
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu szablonów promptów: {e}")
        if 'conn' in locals():
            conn.close()
        return []

def get_prompt_template_by_id(template_id):
    """Pobierz szablon prompta po ID"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM prompt_templates WHERE id = ?", (template_id,))
        
        template_data = cursor.fetchone()
        conn.close()
        
        if template_data:
            return {
                'id': template_data[0],
                'name': template_data[1],
                'description': template_data[2],
                'prompt_text': template_data[3],
                'is_active': bool(template_data[4]),
                'created_at': template_data[5]
            }
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu szablonu prompta: {e}")
        if 'conn' in locals():
            conn.close()
    
    return None

def init_themes_table():
    """Inicjalizuje tabelę tematów konwersacji"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Tabela tematów konwersacji
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_themes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            theme_name TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            last_used_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        ''')
        
        # Dodaj pole theme_id do tabeli conversations
        cursor.execute("PRAGMA table_info(conversations)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'theme_id' not in column_names:
            cursor.execute("ALTER TABLE conversations ADD COLUMN theme_id INTEGER")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Błąd inicjalizacji tabeli tematów: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def create_conversation_theme(user_id, theme_name):
    """
    Tworzy nowy temat konwersacji dla użytkownika
    
    Args:
        user_id (int): ID użytkownika
        theme_name (str): Nazwa tematu
    
    Returns:
        dict: Dane utworzonego tematu lub None w przypadku błędu
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.datetime.now(pytz.UTC).isoformat()
        
        cursor.execute(
            "INSERT INTO conversation_themes (user_id, theme_name, created_at, last_used_at) VALUES (?, ?, ?, ?)",
            (user_id, theme_name, now, now)
        )
        
        theme_id = cursor.lastrowid
        conn.commit()
        
        # Pobierz utworzony temat
        cursor.execute("SELECT * FROM conversation_themes WHERE id = ?", (theme_id,))
        theme_data = cursor.fetchone()
        conn.close()
        
        if theme_data:
            return {
                'id': theme_data[0],
                'user_id': theme_data[1],
                'theme_name': theme_data[2],
                'is_active': bool(theme_data[3]),
                'created_at': theme_data[4],
                'last_used_at': theme_data[5]
            }
        
        return None
    except Exception as e:
        logger.error(f"Błąd przy tworzeniu tematu konwersacji: {e}")
        if 'conn' in locals():
            conn.close()
        return None

def get_user_themes(user_id):
    """
    Pobiera listę tematów konwersacji użytkownika
    
    Args:
        user_id (int): ID użytkownika
    
    Returns:
        list: Lista tematów konwersacji
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM conversation_themes WHERE user_id = ? AND is_active = 1 ORDER BY last_used_at DESC",
            (user_id,)
        )
        
        themes = cursor.fetchall()
        conn.close()
        
        result = []
        for theme in themes:
            result.append({
                'id': theme[0],
                'user_id': theme[1],
                'theme_name': theme[2],
                'is_active': bool(theme[3]),
                'created_at': theme[4],
                'last_used_at': theme[5]
            })
        
        return result
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu tematów konwersacji: {e}")
        if 'conn' in locals():
            conn.close()
        return []

def get_theme_by_id(theme_id):
    """
    Pobiera temat konwersacji po ID
    
    Args:
        theme_id (int): ID tematu
    
    Returns:
        dict: Dane tematu lub None w przypadku błędu
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM conversation_themes WHERE id = ?", (theme_id,))
        theme = cursor.fetchone()
        conn.close()
        
        if theme:
            return {
                'id': theme[0],
                'user_id': theme[1],
                'theme_name': theme[2],
                'is_active': bool(theme[3]),
                'created_at': theme[4],
                'last_used_at': theme[5]
            }
        
        return None
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu tematu konwersacji: {e}")
        if 'conn' in locals():
            conn.close()
        return None

def create_themed_conversation(user_id, theme_id):
    """
    Tworzy nową konwersację dla określonego tematu
    
    Args:
        user_id (int): ID użytkownika
        theme_id (int): ID tematu
    
    Returns:
        dict: Dane utworzonej konwersacji lub None w przypadku błędu
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.datetime.now(pytz.UTC).isoformat()
        
        cursor.execute(
            "INSERT INTO conversations (user_id, created_at, last_message_at, theme_id) VALUES (?, ?, ?, ?)",
            (user_id, now, now, theme_id)
        )
        
        conversation_id = cursor.lastrowid
        
        # Aktualizuj czas ostatniego użycia tematu
        cursor.execute(
            "UPDATE conversation_themes SET last_used_at = ? WHERE id = ?",
            (now, theme_id)
        )
        
        conn.commit()
        
        # Pobierz utworzoną konwersację
        cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        conversation_data = cursor.fetchone()
        conn.close()
        
        if conversation_data:
            return {
                'id': conversation_data[0],
                'user_id': conversation_data[1],
                'created_at': conversation_data[2],
                'last_message_at': conversation_data[3],
                'theme_id': conversation_data[4] if len(conversation_data) > 4 else None
            }
        
        return None
    except Exception as e:
        logger.error(f"Błąd przy tworzeniu konwersacji dla tematu: {e}")
        if 'conn' in locals():
            conn.close()
        return None

def get_active_themed_conversation(user_id, theme_id):
    """
    Pobiera aktywną konwersację dla określonego tematu
    
    Args:
        user_id (int): ID użytkownika
        theme_id (int): ID tematu
    
    Returns:
        dict: Dane konwersacji lub None w przypadku błędu
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM conversations WHERE user_id = ? AND theme_id = ? ORDER BY last_message_at DESC LIMIT 1",
            (user_id, theme_id)
        )
        
        conversation_data = cursor.fetchone()
        conn.close()
        
        if conversation_data:
            return {
                'id': conversation_data[0],
                'user_id': conversation_data[1],
                'created_at': conversation_data[2],
                'last_message_at': conversation_data[3],
                'theme_id': conversation_data[4] if len(conversation_data) > 4 else None
            }
        
        # Jeśli nie znaleziono konwersacji dla tego tematu, utwórz nową
        return create_themed_conversation(user_id, theme_id)
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu aktywnej konwersacji dla tematu: {e}")
        if 'conn' in locals():
            conn.close()
        return None