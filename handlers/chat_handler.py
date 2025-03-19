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