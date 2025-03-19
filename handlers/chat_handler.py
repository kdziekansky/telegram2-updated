from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from config import DEFAULT_MODEL, MAX_CONTEXT_MESSAGES, AVAILABLE_MODELS, CHAT_MODES
from database.sqlite_client import (
    check_active_subscription, get_active_conversation, 
    save_message, get_conversation_history, check_message_limit,
    increment_messages_used, get_message_status
)
from utils.openai_client import chat_completion_stream, prepare_messages_from_history
from utils.translations import get_text
from handlers.menu_handler import get_user_language
import asyncio

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa wiadomości tekstowych od użytkownika ze strumieniowaniem odpowiedzi"""
    user_id = update.effective_user.id
    user_message = update.message.text
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy użytkownik ma dostępne wiadomości
    if not check_message_limit(user_id):
        await update.message.reply_text(get_text("subscription_expired", language))
        return
    
    # Pobierz lub utwórz aktywną konwersację
    conversation = get_active_conversation(user_id)
    conversation_id = conversation['id']
    
    # Zapisz wiadomość użytkownika do bazy danych
    save_message(conversation_id, user_id, user_message, is_from_user=True)
    
    # Wyślij informację, że bot pisze
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    # Pobierz historię konwersacji
    history = get_conversation_history(conversation_id, limit=MAX_CONTEXT_MESSAGES)
    
    # Określ model do użycia - domyślny lub wybrany przez użytkownika
    model_to_use = DEFAULT_MODEL
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_model' in user_data:
            model_to_use = user_data['current_model']
    
    # Przygotuj system prompt - domyślny lub z wybranego trybu
    system_prompt = CHAT_MODES["no_mode"]["prompt"]
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_mode' in user_data and user_data['current_mode'] in CHAT_MODES:
            system_prompt = CHAT_MODES[user_data['current_mode']]["prompt"]
    
    # Przygotuj wiadomości dla API OpenAI
    messages = prepare_messages_from_history(history, user_message, system_prompt)
    
    # Wyślij początkową pustą wiadomość, którą będziemy aktualizować
    response_message = await update.message.reply_text(get_text("generating_response", language))
    
    # Zainicjuj pełną odpowiedź
    full_response = ""
    buffer = ""
    last_update = asyncio.get_event_loop().time()
    
    # Generuj odpowiedź strumieniowo
    async for chunk in chat_completion_stream(messages, model=model_to_use):
        full_response += chunk
        buffer += chunk
        
        # Aktualizuj wiadomość co 1 sekundę lub gdy bufor jest wystarczająco duży
        current_time = asyncio.get_event_loop().time()
        if current_time - last_update >= 1.0 or len(buffer) > 100:
            try:
                # Dodaj migający kursor na końcu wiadomości
                await response_message.edit_text(full_response + "▌", parse_mode=ParseMode.MARKDOWN)
                buffer = ""
                last_update = current_time
            except Exception as e:
                # Jeśli wystąpi błąd (np. wiadomość nie została zmieniona), kontynuuj
                pass
                
    # Aktualizuj wiadomość z pełną odpowiedzią bez kursora
    try:
        await response_message.edit_text(full_response, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        # Jeśli wystąpi błąd formatowania Markdown, wyślij bez formatowania
        await response_message.edit_text(full_response)
    
    # Zapisz odpowiedź do bazy danych
    save_message(conversation_id, user_id, full_response, is_from_user=False, model_used=model_to_use)
    
    # Zwiększ licznik wykorzystanych wiadomości
    increment_messages_used(user_id)
    
    # Sprawdź, ile pozostało wiadomości
    message_status = get_message_status(user_id)
    if message_status["messages_left"] <= 5 and message_status["messages_left"] > 0:
        await update.message.reply_text(
            f"{get_text('low_credits_warning', language)} {get_text('low_credits_message', language, credits=message_status['messages_left'])}",
            parse_mode=ParseMode.MARKDOWN
        )

# Lista porad do rotacji
TIPS = [
    "Krótsze pytania zazwyczaj zużywają mniej kredytów niż długie opisy.",
    "Używaj trybu GPT-3.5 dla prostych pytań, a GPT-4 tylko dla złożonych zadań.",
    "Możesz zaoszczędzić kredyty używając /mode aby wybrać tańszy model.",
    "Zdjęcia z wyraźnym tekstem dają lepsze wyniki przy tłumaczeniu.",
    "Zaproś znajomych przez program referencyjny, aby otrzymać darmowe kredyty.",
    "Używanie komend jest często szybsze niż nawigacja przez menu.",
    "Eksportuj swoje konwersacje do PDF używając komendy /export.",
    "Podziel konwersacje na tematy, aby łatwiej je organizować.",
    "Wypróbuj różne tryby czatu, aby znaleźć najlepszy dla twojego zadania.",
    "Możesz tłumaczyć tekst ze zdjęć używając komendy /translate."
]

# Zmodyfikowana funkcja message_handler z dodanym systemem porad
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa wiadomości tekstowych od użytkownika ze strumieniowaniem odpowiedzi"""
    user_id = update.effective_user.id
    user_message = update.message.text
    language = get_user_language(context, user_id)
    
    # Inicjalizacja danych użytkownika, jeśli nie istnieją
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    # Inicjalizacja licznika interakcji i ustawień porad, jeśli nie istnieją
    if 'interaction_count' not in context.chat_data['user_data'][user_id]:
        context.chat_data['user_data'][user_id]['interaction_count'] = 0
    
    if 'show_tips' not in context.chat_data['user_data'][user_id]:
        context.chat_data['user_data'][user_id]['show_tips'] = True
    
    # Zwiększ licznik interakcji
    context.chat_data['user_data'][user_id]['interaction_count'] += 1
    
    # Kontynuacja standardowej obsługi wiadomości
    # Sprawdź, czy użytkownik ma dostępne wiadomości
    if not check_message_limit(user_id):
        await update.message.reply_text(get_text("subscription_expired", language))
        return
    
    # Pobierz lub utwórz aktywną konwersację
    conversation = get_active_conversation(user_id)
    conversation_id = conversation['id']
    
    # Zapisz wiadomość użytkownika do bazy danych
    save_message(conversation_id, user_id, user_message, is_from_user=True)
    
    # Wyślij informację, że bot pisze
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    # Pobierz historię konwersacji
    history = get_conversation_history(conversation_id, limit=MAX_CONTEXT_MESSAGES)
    
    # Określ model do użycia - domyślny lub wybrany przez użytkownika
    model_to_use = DEFAULT_MODEL
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_model' in user_data:
            model_to_use = user_data['current_model']
    
    # Przygotuj system prompt - domyślny lub z wybranego trybu
    system_prompt = CHAT_MODES["no_mode"]["prompt"]
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_mode' in user_data and user_data['current_mode'] in CHAT_MODES:
            system_prompt = CHAT_MODES[user_data['current_mode']]["prompt"]
    
    # Przygotuj wiadomości dla API OpenAI
    messages = prepare_messages_from_history(history, user_message, system_prompt)
    
    # Wyślij początkową pustą wiadomość, którą będziemy aktualizować
    response_message = await update.message.reply_text(get_text("generating_response", language))
    
    # Zainicjuj pełną odpowiedź
    full_response = ""
    buffer = ""
    last_update = asyncio.get_event_loop().time()
    
    # Generuj odpowiedź strumieniowo
    async for chunk in chat_completion_stream(messages, model=model_to_use):
        full_response += chunk
        buffer += chunk
        
        # Aktualizuj wiadomość co 1 sekundę lub gdy bufor jest wystarczająco duży
        current_time = asyncio.get_event_loop().time()
        if current_time - last_update >= 1.0 or len(buffer) > 100:
            try:
                # Dodaj migający kursor na końcu wiadomości
                await response_message.edit_text(full_response + "▌", parse_mode=ParseMode.MARKDOWN)
                buffer = ""
                last_update = current_time
            except Exception as e:
                # Jeśli wystąpi błąd (np. wiadomość nie została zmieniona), kontynuuj
                pass
    
    # Sprawdź, czy należy pokazać poradę (co 5-7 interakcji)
    show_tip = False
    if (context.chat_data['user_data'][user_id]['interaction_count'] % 6 == 0 and 
        context.chat_data['user_data'][user_id]['show_tips']):
        show_tip = True
        
        # Wybierz losową poradę
        import random
        tip = random.choice(TIPS)
        
        # Dodaj poradę do odpowiedzi
        full_response_with_tip = full_response + f"\n\n💡 *Porada:* {tip}"
        
        # Dodaj przycisk do wyłączenia porad
        keyboard = [[InlineKeyboardButton("Nie pokazuj więcej porad", callback_data="disable_tips")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Aktualizuj wiadomość z poradą
        try:
            await response_message.edit_text(
                full_response_with_tip, 
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        except Exception as e:
            # Jeśli wystąpi błąd formatowania, wyślij bez formatowania
            await response_message.edit_text(
                full_response_with_tip,
                reply_markup=reply_markup
            )
    else:
        # Standardowa aktualizacja wiadomości bez porady
        try:
            await response_message.edit_text(full_response, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            # Jeśli wystąpi błąd formatowania Markdown, wyślij bez formatowania
            await response_message.edit_text(full_response)
    
    # Zapisz odpowiedź do bazy danych - zawsze zapisuj bez porady
    save_message(conversation_id, user_id, full_response, is_from_user=False, model_used=model_to_use)
    
    # Zwiększ licznik wykorzystanych wiadomości
    increment_messages_used(user_id)
    
    # Sprawdź, ile pozostało wiadomości
    message_status = get_message_status(user_id)
    if message_status["messages_left"] <= 5 and message_status["messages_left"] > 0:
        # Dodaj przycisk do zakupu kredytów
        keyboard = [[InlineKeyboardButton("🛒 " + get_text("buy_credits_btn", language), callback_data="menu_credits_buy")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"*{get_text('low_credits_warning', language)}* {get_text('low_credits_message', language, credits=message_status['messages_left'])}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

# Obsługa wyłączania porad - dodaj do handlera callbacków
async def handle_disable_tips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje wyłączanie porad przez użytkownika"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Oznacz, że użytkownik wyłączył porady
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    context.chat_data['user_data'][user_id]['show_tips'] = False
    
    # Usuń przyciski z wiadomości
    try:
        if hasattr(query.message, 'caption'):
            await query.edit_message_caption(
                caption=query.message.caption,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(
                text=query.message.text,
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        # Jeśli wystąpi błąd, zignoruj go - prawdopodobnie wiadomość nie została zmieniona
        pass
    
    # Potwierdź wyłączenie porad
    await query.answer("Porady zostały wyłączone. Możesz je włączyć ponownie w ustawieniach.")