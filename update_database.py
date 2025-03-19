import sqlite3
import logging

# Konfiguracja loggera
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ścieżka do pliku bazy danych
DB_PATH = "bot_database.sqlite"

def update_database_credits():
    """
    Aktualizuje schemat bazy danych, dodając tabelę i pola potrzebne do obsługi
    systemu kredytów.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Dodaj tabelę kredytów użytkownika
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_credits (
            user_id INTEGER PRIMARY KEY,
            credits_amount INTEGER DEFAULT 0,
            total_credits_purchased INTEGER DEFAULT 0,
            last_purchase_date TEXT,
            total_spent REAL DEFAULT 0
        )
        ''')
        
        # Dodaj tabelę transakcji kredytów
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS credit_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            credits_before INTEGER NOT NULL,
            credits_after INTEGER NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        ''')
        
        # Dodaj tabelę pakietów kredytów
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS credit_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            credits INTEGER NOT NULL,
            price REAL NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
        ''')
        
        # Dodaj domyślne pakiety kredytów
        cursor.execute("SELECT COUNT(*) FROM credit_packages")
        if cursor.fetchone()[0] == 0:
            # Jeśli nie ma pakietów, dodaj domyślne
            import datetime
            import pytz
            now = datetime.datetime.now(pytz.UTC).isoformat()
            
            packages = [
                ("Starter", 100, 4.99, now),
                ("Standard", 300, 13.99, now),
                ("Premium", 700, 29.99, now),
                ("Pro", 1500, 59.99, now),
                ("Biznes", 5000, 179.99, now)
            ]
            
            cursor.executemany(
                "INSERT INTO credit_packages (name, credits, price, created_at) VALUES (?, ?, ?, ?)",
                packages
            )
        
        # Zatwierdzenie zmian
        conn.commit()
        logger.info("Aktualizacja schematu bazy danych kredytów zakończona pomyślnie")
        
        # Wyświetl informacje o aktualnym schemacie
        logger.info("Aktualny schemat tabeli user_credits:")
        cursor.execute("PRAGMA table_info(user_credits)")
        for column in cursor.fetchall():
            logger.info(f" - {column[1]} ({column[2]})")
        
        logger.info("Aktualny schemat tabeli credit_transactions:")
        cursor.execute("PRAGMA table_info(credit_transactions)")
        for column in cursor.fetchall():
            logger.info(f" - {column[1]} ({column[2]})")
        
        logger.info("Aktualny schemat tabeli credit_packages:")
        cursor.execute("PRAGMA table_info(credit_packages)")
        for column in cursor.fetchall():
            logger.info(f" - {column[1]} ({column[2]})")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Błąd podczas aktualizacji schematu bazy danych kredytów: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def run_all_updates():
    """
    Uruchamia wszystkie funkcje aktualizujące bazę danych
    """
    logger.info("Rozpoczynam pełną aktualizację bazy danych")
    
    # Aktualizacja tabel kredytów
    update_result = update_database_credits()
    
    # Inicjalizacja tabel tematów konwersacji
    from database.sqlite_client import init_themes_table
    init_themes_table()
    
    logger.info("Zakończono pełną aktualizację bazy danych")
    return update_result

if __name__ == "__main__":
    print("Rozpoczynam aktualizację schematu bazy danych kredytów...")
    result = update_database_credits()
    if result:
        print("Aktualizacja zakończona pomyślnie!")
    else:
        print("Wystąpił błąd podczas aktualizacji. Sprawdź logi.")