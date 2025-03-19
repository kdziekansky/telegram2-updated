# utils/credit_analytics.py
import sqlite3
import datetime
import pytz
import matplotlib.pyplot as plt
import io
from matplotlib.dates import DateFormatter
import numpy as np

# Ścieżka do pliku bazy danych
DB_PATH = "bot_database.sqlite"

def generate_credit_usage_chart(user_id, days=30):
    """
    Generuje wykres użycia kredytów w czasie
    
    Args:
        user_id (int): ID użytkownika
        days (int): Liczba dni do uwzględnienia w analizie
    
    Returns:
        BytesIO: Bufor zawierający wygenerowany wykres
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Pobierz transakcje z ostatnich X dni
        start_date = (datetime.datetime.now(pytz.UTC) - datetime.timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT created_at, transaction_type, amount, credits_after
            FROM credit_transactions
            WHERE user_id = ? AND created_at >= ?
            ORDER BY created_at ASC
        """, (user_id, start_date))
        
        transactions = cursor.fetchall()
        conn.close()
        
        if not transactions:
            return None
        
        # Przygotuj dane do wykresu
        dates = []
        balances = []
        usage_amounts = []
        purchase_amounts = []
        
        for created_at, trans_type, amount, credits_after in transactions:
            try:
                # Konwersja formatu daty
                dt = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                dates.append(dt)
                balances.append(credits_after)
                
                if trans_type == 'deduct':
                    usage_amounts.append(amount)
                    purchase_amounts.append(0)
                elif trans_type in ['add', 'purchase']:
                    usage_amounts.append(0)
                    purchase_amounts.append(amount)
            except Exception as e:
                print(f"Błąd przy przetwarzaniu transakcji: {e}")
        
        # Wygeneruj wykres
        plt.figure(figsize=(10, 6))
        
        # Wykres salda
        plt.subplot(2, 1, 1)
        plt.plot(dates, balances, 'b-', label='Saldo kredytów')
        plt.xlabel('Data')
        plt.ylabel('Kredyty')
        plt.title('Historia salda kredytów')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.gca().xaxis.set_major_formatter(DateFormatter('%d-%m-%Y'))
        plt.gcf().autofmt_xdate()
        plt.legend()
        
        # Wykres transakcji
        plt.subplot(2, 1, 2)
        
        # Przygotuj dane do wykresu słupkowego
        unique_dates = sorted(list(set([d.date() for d in dates])))
        daily_usage = [0] * len(unique_dates)
        daily_purchases = [0] * len(unique_dates)
        
        for i, (dt, usage, purchase) in enumerate(zip(dates, usage_amounts, purchase_amounts)):
            date_idx = unique_dates.index(dt.date())
            daily_usage[date_idx] += usage
            daily_purchases[date_idx] += purchase
        
        x = np.arange(len(unique_dates))
        bar_width = 0.35
        
        plt.bar(x - bar_width/2, daily_usage, bar_width, label='Zużycie', color='red', alpha=0.7)
        plt.bar(x + bar_width/2, daily_purchases, bar_width, label='Zakupy', color='green', alpha=0.7)
        
        plt.xlabel('Data')
        plt.ylabel('Kredyty')
        plt.title('Dzienne zużycie i zakupy kredytów')
        plt.xticks(x, [d.strftime('%d-%m') for d in unique_dates], rotation=45)
        plt.grid(True, linestyle='--', alpha=0.3, axis='y')
        plt.legend()
        
        plt.tight_layout()
        
        # Zapisz wykres do bufora
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        
        return buf
    except Exception as e:
        print(f"Błąd przy generowaniu wykresu: {e}")
        if 'plt' in locals():
            plt.close()
        return None

def get_credit_usage_breakdown(user_id, days=30):
    """
    Pobiera rozkład zużycia kredytów według rodzaju operacji
    
    Args:
        user_id (int): ID użytkownika
        days (int): Liczba dni do uwzględnienia w analizie
    
    Returns:
        dict: Słownik z rozkładem zużycia kredytów
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Pobierz transakcje z ostatnich X dni
        start_date = (datetime.datetime.now(pytz.UTC) - datetime.timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT description, SUM(amount)
            FROM credit_transactions
            WHERE user_id = ? AND created_at >= ? AND transaction_type = 'deduct'
            GROUP BY description
            ORDER BY SUM(amount) DESC
        """, (user_id, start_date))
        
        usage_breakdown = cursor.fetchall()
        conn.close()
        
        result = {}
        for description, amount in usage_breakdown:
            category = "Inne"
            if description:
                if "Wiadomość" in description:
                    category = "Wiadomości"
                elif "obraz" in description or "DALL-E" in description:
                    category = "Obrazy"
                elif "dokument" in description:
                    category = "Analiza dokumentów"
                elif "zdjęci" in description or "zdjęc" in description:
                    category = "Analiza zdjęć"
            
            if category not in result:
                result[category] = 0
            result[category] += amount
        
        return result
    except Exception as e:
        print(f"Błąd przy pobieraniu rozkładu zużycia kredytów: {e}")
        if 'conn' in locals():
            conn.close()
        return {}

def generate_usage_breakdown_chart(user_id, days=30):
    """
    Generuje wykres kołowy rozkładu zużycia kredytów
    
    Args:
        user_id (int): ID użytkownika
        days (int): Liczba dni do uwzględnienia w analizie
    
    Returns:
        BytesIO: Bufor zawierający wygenerowany wykres
    """
    try:
        # Pobierz rozkład zużycia kredytów
        usage_breakdown = get_credit_usage_breakdown(user_id, days)
        
        if not usage_breakdown:
            return None
        
        # Wygeneruj wykres kołowy
        plt.figure(figsize=(8, 6))
        
        labels = list(usage_breakdown.keys())
        sizes = list(usage_breakdown.values())
        colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#c2c2f0']
        
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, shadow=True)
        plt.axis('equal')
        plt.title(f'Rozkład zużycia kredytów w ostatnich {days} dniach')
        
        # Zapisz wykres do bufora
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        
        return buf
    except Exception as e:
        print(f"Błąd przy generowaniu wykresu rozkładu zużycia: {e}")
        if 'plt' in locals():
            plt.close()
        return None

def predict_credit_depletion(user_id, days=30):
    """
    Przewiduje, kiedy skończą się kredyty użytkownika na podstawie historii użycia
    
    Args:
        user_id (int): ID użytkownika
        days (int): Liczba dni do uwzględnienia w analizie
    
    Returns:
        dict: Słownik z informacjami o przewidywanym wyczerpaniu kredytów
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Pobierz aktualne saldo
        cursor.execute("SELECT credits_amount FROM user_credits WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return None
        
        current_balance = result[0]
        
        # Pobierz transakcje z ostatnich X dni
        start_date = (datetime.datetime.now(pytz.UTC) - datetime.timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT SUM(amount) 
            FROM credit_transactions 
            WHERE user_id = ? AND created_at >= ? AND transaction_type = 'deduct'
        """, (user_id, start_date))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            return {"days_left": None, "average_daily_usage": 0, "current_balance": current_balance}
        
        total_usage = result[0]
        average_daily_usage = total_usage / days
        
        if average_daily_usage <= 0:
            return {"days_left": None, "average_daily_usage": 0, "current_balance": current_balance}
        
        days_left = int(current_balance / average_daily_usage)
        depletion_date = datetime.datetime.now() + datetime.timedelta(days=days_left)
        
        return {
            "days_left": days_left,
            "depletion_date": depletion_date.strftime("%d.%m.%Y"),
            "average_daily_usage": round(average_daily_usage, 2),
            "current_balance": current_balance
        }
    except Exception as e:
        print(f"Błąd przy przewidywaniu wyczerpania kredytów: {e}")
        if 'conn' in locals():
            conn.close()
        return None