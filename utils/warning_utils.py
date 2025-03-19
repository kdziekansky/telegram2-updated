"""
Moduł zawierający narzędzia do wyświetlania ostrzeżeń i potwierdzeń
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from utils.translations import get_text
import uuid

def create_credit_warning(operation_cost, current_credits, language="pl"):
    """
    Tworzy ostrzeżenie o koszcie operacji
    
    Args:
        operation_cost (int): Koszt operacji w kredytach
        current_credits (int): Aktualny stan kredytów użytkownika
        language (str): Język komunikatów
        
    Returns:
        tuple: (message, reply_markup, operation_id) zawierająca tekst ostrzeżenia, 
               klawiaturę z przyciskami i identyfikator operacji
    """
    # Generuj unikalny identyfikator operacji
    operation_id = str(uuid.uuid4())[:8]
    
    # Przygotuj komunikat ostrzeżenia
    warning_msg = f"⚠️ *{get_text('operation_cost_warning', language, default='Ostrzeżenie o koszcie')}*\n\n"
    warning_msg += f"{get_text('operation_cost', language, default='Ta operacja zużyje')} *{operation_cost}* "
    warning_msg += f"{get_text('credits', language, default='kredytów')}.\n"
    
    # Oblicz pozostałe kredyty po operacji
    remaining = current_credits - operation_cost
    
    # Dodaj informację o pozostałych kredytach
    warning_msg += f"{get_text('remaining_credits', language, default='Pozostanie Ci')}: *{remaining}* "
    warning_msg += f"{get_text('credits', language, default='kredytów')}.\n\n"
    
    # Dodaj prośbę o potwierdzenie
    warning_msg += f"{get_text('confirm_operation', language, default='Czy chcesz kontynuować?')}"
    
    # Przygotuj przyciski potwierdzenia i anulowania
    keyboard = [
        [
            InlineKeyboardButton(
                get_text("confirm", language, default="✅ Potwierdzam"), 
                callback_data=f"confirm_op_{operation_id}"
            ),
            InlineKeyboardButton(
                get_text("cancel", language, default="❌ Anuluj"), 
                callback_data="cancel_operation"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    return warning_msg, reply_markup, operation_id

def create_success_notification(message, language="pl"):
    """
    Tworzy powiadomienie o sukcesie
    
    Args:
        message (str): Treść powiadomienia
        language (str): Język komunikatów
        
    Returns:
        str: Sformatowane powiadomienie o sukcesie
    """
    return f"✅ *{get_text('success', language, default='Sukces')}*\n\n{message}"

def create_error_notification(message, language="pl"):
    """
    Tworzy powiadomienie o błędzie
    
    Args:
        message (str): Treść powiadomienia o błędzie
        language (str): Język komunikatów
        
    Returns:
        str: Sformatowane powiadomienie o błędzie
    """
    return f"❌ *{get_text('error', language, default='Błąd')}*\n\n{message}"

def create_info_notification(message, language="pl"):
    """
    Tworzy powiadomienie informacyjne
    
    Args:
        message (str): Treść powiadomienia
        language (str): Język komunikatów
        
    Returns:
        str: Sformatowane powiadomienie informacyjne
    """
    return f"ℹ️ *{get_text('info', language, default='Informacja')}*\n\n{message}"

def create_feature_notification(feature_name, description, language="pl"):
    """
    Tworzy powiadomienie o nowej funkcji
    
    Args:
        feature_name (str): Nazwa nowej funkcji
        description (str): Opis nowej funkcji
        language (str): Język komunikatów
        
    Returns:
        tuple: (message, reply_markup) zawierająca tekst powiadomienia i klawiaturę z przyciskami
    """
    # Przygotuj komunikat o nowej funkcji
    message = f"🆕 *{get_text('new_feature', language, default='Nowa funkcja')}*: {feature_name}\n\n"
    message += description
    message += f"\n\n{get_text('try_it_now', language, default='Wypróbuj teraz!')}"
    
    # Przygotuj przycisk do wypróbowania funkcji i przycisk do ukrycia powiadomienia
    keyboard = [
        [
            InlineKeyboardButton(
                get_text("try_now", language, default="Wypróbuj teraz"), 
                callback_data=f"try_feature_{feature_name.lower().replace(' ', '_')}"
            )
        ],
        [
            InlineKeyboardButton(
                get_text("not_now", language, default="Nie teraz"), 
                callback_data="hide_notification"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    return message, reply_markup