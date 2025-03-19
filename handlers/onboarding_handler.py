# Ulepszony system onboardingu z mini-zadaniami
# Dodaj ten kod jako nowy plik handlers/onboarding_handler.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from config import BOT_NAME
from utils.translations import get_text
from handlers.menu_handler import get_user_language
import random

# Lista kroków onboardingu z mini-zadaniami
ONBOARDING_STEPS = [
    {
        'id': 'welcome',
        'title': 'Witaj w przewodniku!',
        'description': 'Poznaj wszystkie funkcje bota poprzez serię mini-zadań.',
        'task': 'Kliknij przycisk "Rozpocznij" poniżej, aby rozpocząć.',
        'image_url': 'https://i.imgur.com/kqIj0SC.png',
        'has_task': False
    },
    {
        'id': 'chat',
        'title': 'Czat z AI',
        'description': 'Bot może odpowiadać na Twoje pytania używając różnych modeli AI.',
        'task': 'Zadanie: Napisz proste pytanie do AI, np. "Czym się zajmujesz?"',
        'image_url': 'https://i.imgur.com/kqIj0SC.png',
        'has_task': True,
        'task_keyword': ['kim', 'jesteś', 'czym', 'zajmujesz']
    },
    {
        'id': 'modes',
        'title': 'Tryby czatu',
        'description': 'Bot posiada różne tryby specjalizujące się w konkretnych zadaniach.',
        'task': 'Zadanie: Użyj komendy /mode aby zobaczyć dostępne tryby czatu.',
        'image_url': 'https://i.imgur.com/vyNkgEi.png',
        'has_task': True,
        'task_command': '/mode'
    },
    {
        'id': 'images',
        'title': 'Generowanie obrazów',
        'description': 'Bot może tworzyć unikalne obrazy na podstawie Twoich opisów.',
        'task': 'Zadanie: Użyj komendy /image [opis] aby wygenerować obraz, np. "/image kot na rowerze".',
        'image_url': 'https://i.imgur.com/R3rLbNV.png',
        'has_task': True,
        'task_command': '/image'
    },
    {
        'id': 'credits',
        'title': 'System kredytów',
        'description': 'Korzystanie z bota wymaga kredytów. Różne operacje kosztują różną liczbę kredytów.',
        'task': 'Zadanie: Sprawdź swój stan kredytów używając komendy /credits.',
        'image_url': 'https://i.imgur.com/0SM3Lj0.png',
        'has_task': True,
        'task_command': '/credits'
    },
    {
        'id': 'export',
        'title': 'Eksport konwersacji',
        'description': 'Możesz wyeksportować historię swoich rozmów do pliku PDF.',
        'task': 'Zadanie: Możesz wyeksportować rozmowę używając komendy /export (opcjonalnie).',
        'image_url': 'https://i.imgur.com/xyZLjac.png',
        'has_task': False
    },
    {
        'id': 'finish',
        'title': 'Gratulacje!',
        'description': 'Zakończyłeś przewodnik po funkcjach bota. Teraz znasz już wszystkie podstawowe możliwości!',
        'task': 'Możesz teraz swobodnie korzystać z bota. Użyj komendy /help jeśli będziesz potrzebować pomocy.',
        'image_url': 'https://i.imgur.com/bvPAD9a.png',
        'has_task': False
    }
]

async def onboarding_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rozpoczyna interaktywny przewodnik po funkcjach bota"""
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Inicjalizacja stanu onboardingu
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    # Ustaw początkowy krok onboardingu
    context.chat_data['user_data'][user_id]['onboarding_step'] = 0
    context.chat_data['user_data'][user_id]['onboarding_tasks_completed'] = []
    context.chat_data['user_data'][user_id]['onboarding_active'] = True
    
    # Pobierz pierwszy krok
    step = ONBOARDING_STEPS[0]
    
    # Przygotuj tekst
    text = f"👋 *{step['title']}*\n\n{step['description']}\n\n🎯 *{step['task']}*"
    
    # Przygotuj przyciski
    keyboard = []
    
    # Pierwszy krok ma tylko przycisk "Rozpocznij"
    keyboard.append([
        InlineKeyboardButton("🚀 " + get_text("onboarding_start", language, default="Rozpocznij"), 
                            callback_data="onboarding_next")
    ])
    
    # Dodaj przycisk do pominięcia całego onboardingu
    keyboard.append([
        InlineKeyboardButton(get_text("onboarding_skip", language, default="Pomiń przewodnik"), 
                            callback_data="onboarding_skip")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Wyślij wiadomość z obrazkiem
    await update.message.reply_photo(
        photo=step['image_url'],
        caption=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_onboarding_step(update: Update, context: ContextTypes.DEFAULT_TYPE, next_step=None):
    """Obsługuje przejście do następnego kroku onboardingu"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Pobierz aktualny krok lub ustaw pierwszy, jeśli nie istnieje
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    if 'onboarding_step' not in context.chat_data['user_data'][user_id]:
        context.chat_data['user_data'][user_id]['onboarding_step'] = 0
        context.chat_data['user_data'][user_id]['onboarding_tasks_completed'] = []
    
    # Pobierz aktualny krok lub użyj podanego
    if next_step is not None:
        current_step = next_step
    else:
        current_step = context.chat_data['user_data'][user_id]['onboarding_step']
    
    # Sprawdź, czy to nie jest ostatni krok
    if current_step >= len(ONBOARDING_STEPS):
        current_step = len(ONBOARDING_STEPS) - 1
    
    # Zapisz aktualny krok
    context.chat_data['user_data'][user_id]['onboarding_step'] = current_step
    
    # Pobierz dane kroku
    step = ONBOARDING_STEPS[current_step]
    
    # Sprawdź czy zadanie zostało wykonane
    tasks_completed = context.chat_data['user_data'][user_id].get('onboarding_tasks_completed', [])
    is_task_completed = step['id'] in tasks_completed
    
    # Przygotuj tekst
    text = f"👋 *{step['title']}*\n\n{step['description']}\n\n"
    
    # Dodaj oznaczenie ukończonego zadania lub opis zadania
    if is_task_completed:
        text += f"✅ *Zadanie ukończone!*\n\n"
    elif step['has_task']:
        text += f"🎯 *{step['task']}*\n\n"
    else:
        text += f"{step['task']}\n\n"
    
    # Dodaj wskaźnik postępu
    progress = f"{current_step + 1}/{len(ONBOARDING_STEPS)}"
    text += f"📊 *Postęp: {progress}*"
    
    # Przygotuj przyciski
    keyboard = []
    row = []
    
    # Przycisk wstecz dla wszystkich kroków oprócz pierwszego
    if current_step > 0:
        row.append(
            InlineKeyboardButton("⬅️ " + get_text("onboarding_back", language, default="Wstecz"), 
                                callback_data="onboarding_back")
        )
    
    # Przycisk dalej/zakończ
    if current_step < len(ONBOARDING_STEPS) - 1:
        # Jeśli zadanie musi być wykonane i nie jest ukończone, przycisk jest nieaktywny
        if step['has_task'] and not is_task_completed:
            button_text = "➡️ " + get_text("onboarding_complete_task", language, default="Wykonaj zadanie")
        else:
            button_text = "➡️ " + get_text("onboarding_next", language, default="Dalej")
        
        row.append(InlineKeyboardButton(button_text, callback_data="onboarding_next"))
    else:
        # Ostatni krok - przycisk "Zakończ"
        row.append(
            InlineKeyboardButton("🏁 " + get_text("onboarding_finish", language, default="Zakończ"), 
                                callback_data="onboarding_finish")
        )
    
    keyboard.append(row)
    
    # Dodaj przycisk do pominięcia całego onboardingu
    keyboard.append([
        InlineKeyboardButton(get_text("onboarding_skip", language, default="Pomiń przewodnik"), 
                            callback_data="onboarding_skip")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Aktualizuj wiadomość
    try:
        await query.edit_message_caption(
            caption=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"Błąd przy aktualizacji wiadomości onboardingu: {e}")
        # Spróbuj wysłać nową wiadomość, jeśli aktualizacja się nie powiedzie
        try:
            await query.delete_message()
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=step['image_url'],
                caption=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e2:
            print(f"Drugi błąd przy wysyłaniu wiadomości onboardingu: {e2}")

async def handle_onboarding_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje callbacki związane z onboardingiem"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    await query.answer()
    
    # Sprawdź, czy użytkownik jest w trybie onboardingu
    if ('user_data' not in context.chat_data or 
        user_id not in context.chat_data['user_data'] or 
        'onboarding_active' not in context.chat_data['user_data'][user_id] or 
        not context.chat_data['user_data'][user_id]['onboarding_active']):
        return False
    
    # Obsługa przycisków onboardingu
    if query.data == "onboarding_next":
        # Pobierz aktualny krok
        current_step = context.chat_data['user_data'][user_id]['onboarding_step']
        step = ONBOARDING_STEPS[current_step]
        
        # Sprawdź, czy to krok z zadaniem, które musi być wykonane
        if step['has_task']:
            # Sprawdź, czy zadanie zostało wykonane
            tasks_completed = context.chat_data['user_data'][user_id].get('onboarding_tasks_completed', [])
            if step['id'] not in tasks_completed:
                # Zadanie nie zostało wykonane, pokaż komunikat
                await query.answer(get_text("onboarding_task_required", language, 
                                           default="Najpierw wykonaj zadanie."))
                return True
        
        # Przejdź do następnego kroku
        next_step = min(current_step + 1, len(ONBOARDING_STEPS) - 1)
        await handle_onboarding_step(update, context, next_step)
        return True
    
    elif query.data == "onboarding_back":
        # Przejdź do poprzedniego kroku
        current_step = context.chat_data['user_data'][user_id]['onboarding_step']
        prev_step = max(0, current_step - 1)
        await handle_onboarding_step(update, context, prev_step)
        return True
    
    elif query.data == "onboarding_skip" or query.data == "onboarding_finish":
        # Zakończ onboarding
        context.chat_data['user_data'][user_id]['onboarding_active'] = False
        
        # Wyślij podsumowanie po zakończeniu onboardingu
        completed_tasks = len(context.chat_data['user_data'][user_id].get('onboarding_tasks_completed', []))
        total_tasks = sum(1 for step in ONBOARDING_STEPS if step['has_task'])
        
        # Usuń wiadomość onboardingu
        try:
            await query.message.delete()
        except:
            pass
        
        # Wyślij podsumowanie
        summary = f"🎉 *{get_text('onboarding_completed', language, default='Przewodnik ukończony!')}*\n\n"
        summary += f"{get_text('onboarding_tasks_completed', language, default='Ukończone zadania')}: "
        summary += f"*{completed_tasks}/{total_tasks}*\n\n"
        
        if completed_tasks < total_tasks:
            summary += f"{get_text('onboarding_remaining_tasks', language, default='Możesz w dowolnej chwili wypróbować pozostałe funkcje. Użyj /help, aby zobaczyć dostępne komendy.')}\n\n"
        
        summary += f"{get_text('onboarding_success', language, default='Dziękujemy za przejście przewodnika! Teraz możesz w pełni korzystać z bota.')}"
        
        # Dodaj przycisk do menu głównego
        keyboard = [[InlineKeyboardButton("🏠 " + get_text("main_menu", language, default="Menu główne"), 
                                         callback_data="menu_back_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=summary,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Dodaj bonus kredytowy za ukończenie przynajmniej połowy zadań
        if completed_tasks >= total_tasks / 2:
            from database.credits_client import add_user_credits
            bonus_credits = 10  # 10 kredytów jako bonus
            add_user_credits(user_id, bonus_credits, "Bonus za ukończenie przewodnika")
            
            # Powiadom użytkownika o bonusie
            bonus_message = f"🎁 *{get_text('onboarding_bonus', language, default='Bonus!')}*\n\n"
            bonus_message += f"{get_text('onboarding_bonus_credits', language, default='Otrzymujesz')} *{bonus_credits}* "
            bonus_message += f"{get_text('credits', language, default='kredytów')} "
            bonus_message += f"{get_text('onboarding_bonus_reason', language, default='za ukończenie przewodnika')}!"
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=bonus_message,
                parse_mode=ParseMode.MARKDOWN
            )
        
        return True
    
    return False

def check_onboarding_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sprawdza, czy wiadomość użytkownika jest wykonaniem zadania onboardingu
    
    Args:
        update: Obiekt Update
        context: Kontekst bota
    
    Returns:
        bool: True jeśli zadanie zostało wykonane, False w przeciwnym razie
    """
    # Sprawdź, czy użytkownik jest w trybie onboardingu
    user_id = update.effective_user.id
    
    if ('user_data' not in context.chat_data or 
        user_id not in context.chat_data['user_data'] or 
        'onboarding_active' not in context.chat_data['user_data'][user_id] or 
        not context.chat_data['user_data'][user_id]['onboarding_active']):
        return False
    
    # Pobierz aktualny krok
    current_step = context.chat_data['user_data'][user_id]['onboarding_step']
    step = ONBOARDING_STEPS[current_step]
    
    # Sprawdź, czy to krok z zadaniem
    if not step['has_task']:
        return False
    
    # Sprawdź, czy zadanie zostało już wykonane
    tasks_completed = context.chat_data['user_data'][user_id].get('onboarding_tasks_completed', [])
    if step['id'] in tasks_completed:
        return False
    
    # Sprawdź, czy wiadomość to wykonanie zadania
    if 'task_command' in step:
        # Zadanie wymaga użycia komendy
        if update.message and update.message.text and update.message.text.startswith(step['task_command']):
            # Zadanie wykonane
            if 'onboarding_tasks_completed' not in context.chat_data['user_data'][user_id]:
                context.chat_data['user_data'][user_id]['onboarding_tasks_completed'] = []
            
            context.chat_data['user_data'][user_id]['onboarding_tasks_completed'].append(step['id'])
            return True
    
    elif 'task_keyword' in step:
        # Zadanie wymaga użycia słów kluczowych
        if update.message and update.message.text:
            text = update.message.text.lower()
            # Sprawdź, czy tekst zawiera słowa kluczowe
            if any(keyword in text for keyword in step['task_keyword']):
                # Zadanie wykonane
                if 'onboarding_tasks_completed' not in context.chat_data['user_data'][user_id]:
                    context.chat_data['user_data'][user_id]['onboarding_tasks_completed'] = []
                
                context.chat_data['user_data'][user_id]['onboarding_tasks_completed'].append(step['id'])
                return True
    
    return False

# Ten kod powinien być dodany do pliku main.py, w funkcji obsługującej wiadomości
async def message_handler_with_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Funkcja interceptująca wiadomości i sprawdzająca, czy są częścią onboardingu
    """
    # Sprawdź, czy wiadomość jest związana z onboardingiem
    if check_onboarding_task(update, context):
        user_id = update.effective_user.id
        language = get_user_language(context, user_id)
        
        # Wyślij potwierdzenie wykonania zadania
        current_step = context.chat_data['user_data'][user_id]['onboarding_step']
        step = ONBOARDING_STEPS[current_step]
        
        # Pozwól na standardową obsługę wiadomości, a potem dodaj komunikat o wykonaniu zadania
        # To pozwala na widzenie rezultatu wykonania zadania
        
        # Poczekaj 2 sekundy, aby wiadomość z rezultatem zadania została najpierw wyświetlona
        import asyncio
        await asyncio.sleep(2)
        
        # Wyślij potwierdzenie
        task_message = f"✅ *{get_text('onboarding_task_completed', language, default='Zadanie wykonane!')}*\n\n"
        task_message += f"{get_text('onboarding_can_continue', language, default='Możesz kontynuować przewodnik klikając przycisk \"Dalej\".')}"
        
        await update.message.reply_text(
            task_message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Kontynuuj standardową obsługę wiadomości
        return False
    
    # Kontynuuj standardową obsługę wiadomości
    return False