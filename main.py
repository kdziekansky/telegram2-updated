import logging
import os
import re
import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import ReplyKeyboardRemove
from handlers.help_handler import help_command, check_status
from handlers.translate_handler import translate_command
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode, ChatAction
from config import (
    TELEGRAM_TOKEN, DEFAULT_MODEL, AVAILABLE_MODELS, 
    MAX_CONTEXT_MESSAGES, CHAT_MODES, BOT_NAME, CREDIT_COSTS,
    AVAILABLE_LANGUAGES, ADMIN_USER_IDS
)

# Import funkcji z modułu tłumaczeń
from utils.translations import get_text

# Import funkcji z modułu sqlite_client
from database.sqlite_client import (
    get_or_create_user, create_new_conversation, 
    get_active_conversation, save_message, 
    get_conversation_history, get_message_status
)

# Import funkcji obsługi kredytów
from database.credits_client import (
    get_user_credits, add_user_credits, deduct_user_credits, 
    check_user_credits
)

# Import handlerów kredytów
from handlers.credit_handler import (
    credits_command, buy_command, handle_credit_callback,
    credit_stats_command, credit_analytics_command
)

# Import handlerów kodu aktywacyjnego
from handlers.code_handler import (
    code_command, admin_generate_code
)

# Import handlerów menu
from handlers.menu_handler import (
    handle_menu_callback, set_user_name, get_user_language, store_menu_state
)

# Import handlera start
from handlers.start_handler import (
    start_command, handle_language_selection, language_command
)

# Import handlera obrazów
from handlers.image_handler import generate_image

# Import handlera mode
from handlers.mode_handler import handle_mode_selection, show_modes

from utils.openai_client import (
    chat_completion_stream, prepare_messages_from_history,
    generate_image_dall_e, analyze_document, analyze_image
)

# Import handlera eksportu
from handlers.export_handler import export_conversation
from handlers.theme_handler import theme_command, notheme_command, handle_theme_callback
from utils.credit_analytics import generate_credit_usage_chart, generate_usage_breakdown_chart

# Konfiguracja loggera
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Funkcje onboardingu
async def onboarding_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Przewodnik po funkcjach bota krok po kroku
    Użycie: /onboarding
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Inicjalizacja stanu onboardingu
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    context.chat_data['user_data'][user_id]['onboarding_state'] = 0
    
    # Lista kroków onboardingu
    steps = [
        'welcome', 'chat', 'modes', 'images', 'analysis', 
        'credits', 'referral', 'export', 
        'settings', 'finish'
    ]
    
    # Pobierz aktualny krok
    current_step = 0
    step_name = steps[current_step]
    
    # Przygotuj tekst dla aktualnego kroku
    text = get_text(f"onboarding_{step_name}", language, bot_name=BOT_NAME)
    
    # Przygotuj klawiaturę nawigacyjną
    keyboard = []
    row = []
    
    # Na pierwszym kroku tylko przycisk "Dalej"
    row.append(InlineKeyboardButton(
        get_text("onboarding_next", language), 
        callback_data=f"onboarding_next"
    ))
    
    keyboard.append(row)
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Wysyłamy zdjęcie z podpisem dla pierwszego kroku
    await update.message.reply_photo(
        photo=get_onboarding_image_url(step_name),
        caption=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def get_onboarding_image_url(step_name):
    """
    Zwraca URL obrazu dla danego kroku onboardingu
    """
    # Mapowanie kroków do URL obrazów - każdy krok ma unikalny obraz
    images = {
        'welcome': "https://i.imgur.com/kqIj0SC.png",     # Obrazek powitalny
        'chat': "https://i.imgur.com/kqIj0SC.png",        # Obrazek dla czatu z AI
        'modes': "https://i.imgur.com/vyNkgEi.png",       # Obrazek dla trybów czatu
        'images': "https://i.imgur.com/R3rLbNV.png",      # Obrazek dla generowania obrazów
        'analysis': "https://i.imgur.com/ky7MWTk.png",    # Obrazek dla analizy dokumentów
        'credits': "https://i.imgur.com/0SM3Lj0.png",     # Obrazek dla systemu kredytów
        'referral': "https://i.imgur.com/0I1UjLi.png",    # Obrazek dla programu referencyjnego
        'export': "https://i.imgur.com/xyZLjac.png",      # Obrazek dla eksportu
        'settings': "https://i.imgur.com/XUAAxe9.png",    # Obrazek dla ustawień
        'finish': "https://i.imgur.com/bvPAD9a.png"       # Obrazek dla końca onboardingu
    }
    
    # Użyj odpowiedniego obrazka dla danego kroku lub domyślnego, jeśli nie znaleziono
    return images.get(step_name, "https://i.imgur.com/kqIj0SC.png")

async def handle_onboarding_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługuje przyciski nawigacyjne onboardingu
    """
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    await query.answer()  # Odpowiedz na callback, aby usunąć oczekiwanie
    
    # Inicjalizacja stanu onboardingu jeśli nie istnieje
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    if 'onboarding_state' not in context.chat_data['user_data'][user_id]:
        context.chat_data['user_data'][user_id]['onboarding_state'] = 0
    
    # Pobierz aktualny stan onboardingu
    current_step = context.chat_data['user_data'][user_id]['onboarding_state']
    
    # Lista kroków onboardingu
    steps = [
        'welcome', 'chat', 'modes', 'images', 'analysis', 
        'credits', 'referral', 'export', 'settings', 'finish'
    ]
    
    # Obsługa przycisków
    if query.data == "onboarding_next":
        # Przejdź do następnego kroku
        next_step = min(current_step + 1, len(steps) - 1)
        context.chat_data['user_data'][user_id]['onboarding_state'] = next_step
        step_name = steps[next_step]
    elif query.data == "onboarding_back":
        # Wróć do poprzedniego kroku
        prev_step = max(0, current_step - 1)
        context.chat_data['user_data'][user_id]['onboarding_state'] = prev_step
        step_name = steps[prev_step]
    elif query.data == "onboarding_finish":
        # Usuń stan onboardingu
        if 'onboarding_state' in context.chat_data['user_data'][user_id]:
            del context.chat_data['user_data'][user_id]['onboarding_state']
        
        # Usuń wiadomość onboardingu
        try:
            await query.message.delete()
        except Exception as e:
            print(f"Błąd przy usuwaniu wiadomości onboardingu: {e}")
        
        return
    else:
        # Nieznany callback
        return
    
    # Pobierz aktualny krok po aktualizacji
    current_step = context.chat_data['user_data'][user_id]['onboarding_state']
    step_name = steps[current_step]
    
    # Przygotuj tekst dla aktualnego kroku
    text = get_text(f"onboarding_{step_name}", language, bot_name=BOT_NAME)
    
    # Przygotuj klawiaturę nawigacyjną
    keyboard = []
    row = []
    
    # Przycisk "Wstecz" jeśli nie jesteśmy na pierwszym kroku
    if current_step > 0:
        row.append(InlineKeyboardButton(
            get_text("onboarding_back", language),
            callback_data="onboarding_back"
        ))
    
    # Przycisk "Dalej" lub "Zakończ" w zależności od kroku
    if current_step < len(steps) - 1:
        row.append(InlineKeyboardButton(
            get_text("onboarding_next", language),
            callback_data="onboarding_next"
        ))
    else:
        row.append(InlineKeyboardButton(
            get_text("onboarding_finish_button", language),
            callback_data="onboarding_finish"
        ))
    
    keyboard.append(row)
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Pobierz URL obrazu dla aktualnego kroku
    image_url = get_onboarding_image_url(step_name)
    
    try:
        # Usuń poprzednią wiadomość i wyślij nową z odpowiednim obrazem
        await query.message.delete()
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=image_url,
            caption=text,
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Błąd przy aktualizacji wiadomości onboardingu: {e}")
        try:
            # Jeśli usunięcie i wysłanie nowej wiadomości się nie powiedzie, 
            # próbujemy zaktualizować obecną
            await query.edit_message_caption(
                caption=text,
                reply_markup=reply_markup
            )
        except Exception as e2:
            print(f"Nie udało się zaktualizować wiadomości: {e2}")
                
# Handlers dla podstawowych komend

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługa komendy /restart
    Resetuje kontekst bota, pokazuje informacje o bocie i aktualnych ustawieniach użytkownika
    """
    try:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Resetowanie konwersacji - tworzymy nową konwersację i czyścimy kontekst
        conversation = create_new_conversation(user_id)
        
        # Zachowujemy wybrane ustawienia użytkownika (język, model)
        user_data = {}
        if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
            # Pobieramy tylko podstawowe ustawienia, reszta jest resetowana
            old_user_data = context.chat_data['user_data'][user_id]
            if 'language' in old_user_data:
                user_data['language'] = old_user_data['language']
            if 'current_model' in old_user_data:
                user_data['current_model'] = old_user_data['current_model']
            if 'current_mode' in old_user_data:
                user_data['current_mode'] = old_user_data['current_mode']
        
        # Resetujemy dane użytkownika w kontekście i ustawiamy tylko zachowane ustawienia
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        context.chat_data['user_data'][user_id] = user_data
        
        # Pobierz język użytkownika
        language = get_user_language(context, user_id)
        
        # Wyślij potwierdzenie restartu
        restart_message = get_text("restart_command", language)
        
        # Utwórz klawiaturę menu
        keyboard = [
            [
                InlineKeyboardButton(get_text("menu_chat_mode", language), callback_data="menu_section_chat_modes"),
                InlineKeyboardButton(get_text("image_generate", language), callback_data="menu_image_generate")
            ],
            [
                InlineKeyboardButton(get_text("menu_credits", language), callback_data="menu_section_credits"),
                InlineKeyboardButton(get_text("menu_dialog_history", language), callback_data="menu_section_history")
            ],
            [
                InlineKeyboardButton(get_text("menu_settings", language), callback_data="menu_section_settings"),
                InlineKeyboardButton(get_text("menu_help", language), callback_data="menu_help")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Wyślij wiadomość z menu
        try:
            # Próbuj wysłać wiadomość tekstową zamiast zdjęcia
            message = await context.bot.send_message(
                chat_id=chat_id,
                text=restart_message + "\n\n" + get_text("welcome_message", language, bot_name=BOT_NAME),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Zapisz ID wiadomości menu i stan menu
            store_menu_state(context, user_id, 'main', message.message_id)
            
        except Exception as e:
            print(f"Błąd przy wysyłaniu wiadomości po restarcie: {e}")
            import traceback
            traceback.print_exc()
            
            # Jeśli wysłanie wiadomości z menu się nie powiodło, wyślij prostą wiadomość
            await context.bot.send_message(
                chat_id=chat_id,
                text=restart_message
            )
            
    except Exception as e:
        print(f"Błąd w funkcji restart_command: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            # Używamy context.bot.send_message zamiast update.message.reply_text
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=get_text("restart_error", get_user_language(context, update.effective_user.id))
            )
        except Exception as e2:
            print(f"Błąd przy wysyłaniu wiadomości o błędzie: {e2}")


async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sprawdza status konta użytkownika
    Użycie: /status
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Pobierz status kredytów
    credits = get_user_credits(user_id)
    
    # Pobranie aktualnego trybu czatu
    current_mode = get_text("no_mode", language)
    current_mode_cost = 1
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_mode' in user_data and user_data['current_mode'] in CHAT_MODES:
            mode_id = user_data['current_mode']
            current_mode = get_text(f"chat_mode_{mode_id}", language, default=CHAT_MODES[mode_id]["name"])
            current_mode_cost = CHAT_MODES[mode_id]["credit_cost"]
    
    # Stwórz wiadomość o statusie, używając tłumaczeń
    message = f"""
*{get_text("status_command", language, bot_name=BOT_NAME)}*

{get_text("available_credits", language)}: *{credits}*
{get_text("current_mode", language)}: *{current_mode}* ({get_text("cost", language)}: {current_mode_cost} {get_text("credits_per_message", language)})

{get_text("operation_costs", language)}:
- {get_text("standard_message", language)} (GPT-3.5): 1 {get_text("credit", language)}
- {get_text("premium_message", language)} (GPT-4o): 3 {get_text("credits", language)}
- {get_text("expert_message", language)} (GPT-4): 5 {get_text("credits", language)}
- {get_text("dalle_image", language)}: 10-15 {get_text("credits", language)}
- {get_text("document_analysis", language)}: 5 {get_text("credits", language)}
- {get_text("photo_analysis", language)}: 8 {get_text("credits", language)}

{get_text("buy_more_credits", language)}: /buy.
"""
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rozpoczyna nową konwersację"""
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Utwórz nową konwersację
    conversation = create_new_conversation(user_id)
    
    if conversation:
        await update.message.reply_text(
            get_text("newchat_command", language),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            get_text("new_chat_error", language),
            parse_mode=ParseMode.MARKDOWN
        )

async def show_models(update: Update, context: ContextTypes.DEFAULT_TYPE, edit_message=False, callback_query=None):
    """Pokazuje dostępne modele AI"""
    user_id = update.effective_user.id if hasattr(update, 'effective_user') else callback_query.from_user.id
    language = get_user_language(context, user_id)
    
    # Utwórz przyciski dla dostępnych modeli
    keyboard = []
    for model_id, model_name in AVAILABLE_MODELS.items():
        # Dodaj informację o koszcie kredytów
        credit_cost = CREDIT_COSTS["message"].get(model_id, CREDIT_COSTS["message"]["default"])
        keyboard.append([
            InlineKeyboardButton(
                text=f"{model_name} ({credit_cost} {get_text('credits_per_message', language)})", 
                callback_data=f"model_{model_id}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if edit_message and callback_query:
        await callback_query.edit_message_text(
            get_text("models_command", language),
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            get_text("models_command", language),
            reply_markup=reply_markup
        )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa wiadomości tekstowych od użytkownika ze strumieniowaniem odpowiedzi"""
    user_id = update.effective_user.id
    user_message = update.message.text
    language = get_user_language(context, user_id)
    
    print(f"Otrzymano wiadomość od użytkownika {user_id}: {user_message}")
    
    # Określ tryb i koszt kredytów
    current_mode = "no_mode"
    credit_cost = 1
    
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_mode' in user_data and user_data['current_mode'] in CHAT_MODES:
            current_mode = user_data['current_mode']
            credit_cost = CHAT_MODES[current_mode]["credit_cost"]
    
    print(f"Tryb: {current_mode}, koszt kredytów: {credit_cost}")
    
    # Sprawdź, czy użytkownik ma wystarczającą liczbę kredytów
    has_credits = check_user_credits(user_id, credit_cost)
    print(f"Czy użytkownik ma wystarczająco kredytów: {has_credits}")
    
    if not has_credits:
        await update.message.reply_text(get_text("subscription_expired", language))
        return
    
    # Pobierz lub utwórz aktywną konwersację
    try:
        conversation = get_active_conversation(user_id)
        conversation_id = conversation['id']
        print(f"Aktywna konwersacja: {conversation_id}")
    except Exception as e:
        print(f"Błąd przy pobieraniu konwersacji: {e}")
        await update.message.reply_text("Wystąpił błąd przy pobieraniu konwersacji. Spróbuj /newchat aby utworzyć nową.")
        return
    
    # Zapisz wiadomość użytkownika do bazy danych
    try:
        save_message(conversation_id, user_id, user_message, is_from_user=True)
        print("Wiadomość użytkownika zapisana w bazie")
    except Exception as e:
        print(f"Błąd przy zapisie wiadomości użytkownika: {e}")
    
    # Wyślij informację, że bot pisze
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    # Pobierz historię konwersacji
    try:
        history = get_conversation_history(conversation_id, limit=MAX_CONTEXT_MESSAGES)
        print(f"Pobrano historię konwersacji, liczba wiadomości: {len(history)}")
    except Exception as e:
        print(f"Błąd przy pobieraniu historii: {e}")
        history = []
    
    # Określ model do użycia - domyślny lub z trybu czatu
    model_to_use = CHAT_MODES[current_mode].get("model", DEFAULT_MODEL)
    
    # Jeśli użytkownik wybrał konkretny model, użyj go
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_model' in user_data:
            model_to_use = user_data['current_model']
            # Aktualizuj koszt kredytów na podstawie modelu
            credit_cost = CREDIT_COSTS["message"].get(model_to_use, CREDIT_COSTS["message"]["default"])
    
    print(f"Używany model: {model_to_use}")
    
    # Przygotuj system prompt z wybranego trybu
    system_prompt = CHAT_MODES[current_mode]["prompt"]
    
    # Przygotuj wiadomości dla API OpenAI
    messages = prepare_messages_from_history(history, user_message, system_prompt)
    print(f"Przygotowano {len(messages)} wiadomości dla API")
    
    # Wyślij początkową pustą wiadomość, którą będziemy aktualizować
    response_message = await update.message.reply_text(get_text("generating_response", language))
    
    # Zainicjuj pełną odpowiedź
    full_response = ""
    buffer = ""
    last_update = datetime.datetime.now().timestamp()
    
    # Spróbuj wygenerować odpowiedź
    try:
        print("Rozpoczynam generowanie odpowiedzi strumieniowej...")
        # Generuj odpowiedź strumieniowo
        async for chunk in chat_completion_stream(messages, model=model_to_use):
            full_response += chunk
            buffer += chunk
            
            # Aktualizuj wiadomość co 1 sekundę lub gdy bufor jest wystarczająco duży
            current_time = datetime.datetime.now().timestamp()
            if current_time - last_update >= 1.0 or len(buffer) > 100:
                try:
                    # Dodaj migający kursor na końcu wiadomości
                    await response_message.edit_text(full_response + "▌", parse_mode=ParseMode.MARKDOWN)
                    buffer = ""
                    last_update = current_time
                except Exception as e:
                    # Jeśli wystąpi błąd (np. wiadomość nie została zmieniona), kontynuuj
                    print(f"Błąd przy aktualizacji wiadomości: {e}")
        
        print("Zakończono generowanie odpowiedzi")
        
        # Aktualizuj wiadomość z pełną odpowiedzią bez kursora
        try:
            await response_message.edit_text(full_response, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            # Jeśli wystąpi błąd formatowania Markdown, wyślij bez formatowania
            print(f"Błąd formatowania Markdown: {e}")
            await response_message.edit_text(full_response)
        
        # Zapisz odpowiedź do bazy danych
        save_message(conversation_id, user_id, full_response, is_from_user=False, model_used=model_to_use)
        
        # Odejmij kredyty
        deduct_user_credits(user_id, credit_cost, f"Wiadomość ({model_to_use})")
        print(f"Odjęto {credit_cost} kredytów za wiadomość")
    except Exception as e:
        print(f"Wystąpił błąd podczas generowania odpowiedzi: {e}")
        await response_message.edit_text(f"Wystąpił błąd podczas generowania odpowiedzi: {str(e)}")
        return
    
    # Sprawdź aktualny stan kredytów
    credits = get_user_credits(user_id)
    if credits < 5:
        # Dodaj przycisk doładowania kredytów
        keyboard = [[InlineKeyboardButton("🛒 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="menu_credits_buy")]]
        
        await update.message.reply_text(

f"*{get_text('low_credits_warning', language)}* {get_text('low_credits_message', language, credits=credits)}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa przesłanych dokumentów"""
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy użytkownik ma wystarczającą liczbę kredytów
    credit_cost = CREDIT_COSTS["document"]
    if not check_user_credits(user_id, credit_cost):
        await update.message.reply_text(get_text("subscription_expired", language))
        return
    
    document = update.message.document
    file_name = document.file_name
    
    # Sprawdź rozmiar pliku (limit 25MB)
    if document.file_size > 25 * 1024 * 1024:
        await update.message.reply_text(get_text("file_too_large", language))
        return
    
    # Sprawdź, czy to jest prośba o tłumaczenie
    caption = update.message.caption or ""
    translate_mode = False
    
    if caption.lower().startswith("/translate") or caption.lower().startswith("przetłumacz"):
        translate_mode = True
    
    # Sprawdź, czy plik to PDF i czy jest w trybie tłumaczenia
    is_pdf = file_name.lower().endswith('.pdf')
    
    # Pobierz plik
    if translate_mode and is_pdf:
        from handlers.pdf_handler import handle_pdf_translation
        await handle_pdf_translation(update, context)
        return
    elif translate_mode:
        message = await update.message.reply_text(get_text("translating_document", language))
    else:
        message = await update.message.reply_text(get_text("analyzing_file", language))
    
    # Wyślij informację o aktywności bota
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    file = await context.bot.get_file(document.file_id)
    file_bytes = await file.download_as_bytearray()
    
    # Analizuj plik - w trybie tłumaczenia lub analizy w zależności od opcji
    if translate_mode:
        analysis = await analyze_document(file_bytes, file_name, mode="translate")
        header = f"*{get_text('translated_text', language)}:*\n\n"
    else:
        analysis = await analyze_document(file_bytes, file_name)
        header = f"*{get_text('file_analysis', language)}:* {file_name}\n\n"
    
    # Odejmij kredyty
    description = "Tłumaczenie dokumentu" if translate_mode else "Analiza dokumentu"
    deduct_user_credits(user_id, credit_cost, f"{description}: {file_name}")
    
    # Wyślij analizę do użytkownika
    await message.edit_text(
        f"{header}{analysis}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Dodaj klawiaturę z dodatkowymi opcjami dla plików PDF
    if is_pdf and not translate_mode:
        keyboard = [[
            InlineKeyboardButton(get_text("pdf_translate_button", language), callback_data=f"translate_pdf_{document.file_id}")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await message.edit_reply_markup(reply_markup=reply_markup)
        except Exception as e:
            print(f"Błąd dodawania klawiatury: {e}")
    
    # Sprawdź aktualny stan kredytów
    credits = get_user_credits(user_id)
    if credits < 5:
        await update.message.reply_text(
            f"*{get_text('low_credits_warning', language)}* {get_text('low_credits_message', language, credits=credits)}",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa przesłanych zdjęć"""
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy użytkownik ma wystarczającą liczbę kredytów
    credit_cost = CREDIT_COSTS["photo"]
    if not check_user_credits(user_id, credit_cost):
        await update.message.reply_text(get_text("subscription_expired", language))
        return
    
    # Sprawdź, czy zdjęcie zostało przesłane z komendą tłumaczenia
    caption = update.message.caption or ""
    translate_mode = False
    
    if caption.lower().startswith("/translate") or caption.lower().startswith("przetłumacz"):
        translate_mode = True
    
    # Wybierz zdjęcie o najwyższej rozdzielczości
    photo = update.message.photo[-1]
    
    # Pobierz zdjęcie
    if translate_mode:
        message = await update.message.reply_text("Tłumaczę tekst ze zdjęcia, proszę czekać...")
    else:
        message = await update.message.reply_text(get_text("analyzing_photo", language))
    
    # Wyślij informację o aktywności bota
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    file = await context.bot.get_file(photo.file_id)
    file_bytes = await file.download_as_bytearray()
    
    # Analizuj zdjęcie w odpowiednim trybie
    if translate_mode:
        result = await analyze_image(file_bytes, f"photo_{photo.file_unique_id}.jpg", mode="translate")
        header = "*Tłumaczenie tekstu ze zdjęcia:*\n\n"
    else:
        result = await analyze_image(file_bytes, f"photo_{photo.file_unique_id}.jpg", mode="analyze")
        header = "*Analiza zdjęcia:*\n\n"
    
    # Odejmij kredyty
    description = "Tłumaczenie tekstu ze zdjęcia" if translate_mode else "Analiza zdjęcia"
    deduct_user_credits(user_id, credit_cost, description)
    
    # Wyślij analizę/tłumaczenie do użytkownika
    await message.edit_text(
        f"{header}{result}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Dodaj klawiaturę z dodatkowymi opcjami
    if not translate_mode:
        keyboard = [[
            InlineKeyboardButton("🔄 Przetłumacz tekst z tego zdjęcia", callback_data=f"translate_photo_{photo.file_id}")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await message.edit_reply_markup(reply_markup=reply_markup)
        except Exception as e:
            print(f"Błąd dodawania klawiatury: {e}")
    
    # Sprawdź aktualny stan kredytów
    credits = get_user_credits(user_id)
    if credits < 5:
        await update.message.reply_text(
            f"*Uwaga:* Pozostało Ci tylko *{credits}* kredytów. "
            f"Kup więcej za pomocą komendy /buy.",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_photo_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa przesłanych zdjęć z poleceniem tłumaczenia tekstu"""
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy użytkownik ma wystarczającą liczbę kredytów
    credit_cost = CREDIT_COSTS["photo"]
    if not check_user_credits(user_id, credit_cost):
        await update.message.reply_text(get_text("subscription_expired", language))
        return
    
    # Wybierz zdjęcie o najwyższej rozdzielczości
    photo = update.message.photo[-1]
    
    # Pobierz zdjęcie
    message = await update.message.reply_text("Tłumaczę tekst ze zdjęcia, proszę czekać...")
    
    # Wyślij informację o aktywności bota
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    file = await context.bot.get_file(photo.file_id)
    file_bytes = await file.download_as_bytearray()
    
    # Analizuj zdjęcie w trybie tłumaczenia
    translation = await analyze_image(file_bytes, f"photo_{photo.file_unique_id}.jpg", mode="translate")
    
    # Odejmij kredyty
    deduct_user_credits(user_id, credit_cost, "Tłumaczenie tekstu ze zdjęcia")
    
    # Wyślij tłumaczenie do użytkownika
    await message.edit_text(
        f"*Tłumaczenie tekstu ze zdjęcia:*\n\n{translation}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Sprawdź aktualny stan kredytów
    credits = get_user_credits(user_id)
    if credits < 5:
        await update.message.reply_text(
            f"*Uwaga:* Pozostało Ci tylko *{credits}* kredytów. "
            f"Kup więcej za pomocą komendy /buy.",
            parse_mode=ParseMode.MARKDOWN
        )
        
async def show_translation_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Wyświetla instrukcje dotyczące tłumaczenia tekstu ze zdjęć
    """
    await update.message.reply_text(
        "📸 *Tłumaczenie tekstu ze zdjęć*\n\n"
        "Masz kilka sposobów, aby przetłumaczyć tekst ze zdjęcia:\n\n"
        "1️⃣ Wyślij zdjęcie, a następnie kliknij przycisk \"🔄 Przetłumacz tekst z tego zdjęcia\" pod analizą\n\n"
        "2️⃣ Wyślij zdjęcie z podpisem \"/translate\" lub \"przetłumacz\"\n\n"
        "3️⃣ Użyj komendy /translate a następnie wyślij zdjęcie\n\n"
        "Bot rozpozna tekst na zdjęciu i przetłumaczy go na język polski. "
        "Ta funkcja jest przydatna do tłumaczenia napisów, dokumentów, menu, znaków itp.",
        parse_mode=ParseMode.MARKDOWN
    )

# Handlers dla przycisków i callbacków

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa zapytań zwrotnych (z przycisków)"""
    query = update.callback_query
    
    # Dodaj debugowanie
    print(f"Otrzymano callback: {query.data}")
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Zawsze odpowiadaj na callback, aby usunąć oczekiwanie
    await query.answer()
    
    # Obsługa przycisków onboardingu
    if query.data.startswith("onboarding_"):
        await handle_onboarding_callback(update, context)
        return
    
    # Najpierw sprawdzamy, czy to callback związany z menu
    if query.data.startswith("menu_"):
        print(f"Rozpoznano callback menu: {query.data}")
        try:
            # Importuj funkcję obsługi menu
            from handlers.menu_handler import handle_menu_callback
            result = await handle_menu_callback(update, context)
            print(f"Wynik obsługi menu: {result}")
            if result:
                return
            # Jeśli menu_handler nie obsłużył callbacku, kontynuujemy poniżej
        except Exception as e:
            print(f"Błąd w obsłudze menu: {str(e)}")
            import traceback
            traceback.print_exc()
            # Wyślij informację o błędzie
            try:
                # Sprawdź, czy wiadomość ma podpis (jest to zdjęcie lub inny typ mediów)
                if hasattr(query.message, 'caption'):
                    await query.edit_message_caption(
                        caption=f"Wystąpił błąd podczas obsługi menu: {str(e)}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await query.edit_message_text(
                        text=f"Wystąpił błąd podczas obsługi menu: {str(e)}",
                        parse_mode=ParseMode.MARKDOWN
                    )
            except:
                pass
    
    # Obsługa wyboru języka
    if query.data.startswith("start_lang_"):
        from handlers.start_handler import handle_language_selection
        await handle_language_selection(update, context)
        return
    
    # Dodaj to w sekcji obsługi callbacków w funkcji handle_callback_query
    if query.data == "menu_home":
    # Wywołaj funkcję powrotu do głównego menu
        await handle_back_to_main(update, context)
        return

    # Obsługa przycisku wyboru modelu
    if query.data.startswith("model_"):
        model_id = query.data[6:]  # Pobierz ID modelu (usuń prefix "model_")
        await handle_model_selection(update, context, model_id)
        return
    
    # Obsługa przycisków ustawień
    elif query.data.startswith("settings_"):
        print(f"Rozpoznano callback ustawień: {query.data}")
        try:
            from handlers.menu_handler import handle_menu_callback
            result = await handle_menu_callback(update, context)
            if not result:
                await query.answer("Funkcja w trakcie implementacji.")
            return
        except Exception as e:
            print(f"Błąd w obsłudze ustawień: {str(e)}")
            import traceback
            traceback.print_exc()
            await query.answer(f"Error: {str(e)}")
            return
    
    # Obsługa wyboru trybu czatu
    if query.data.startswith("mode_"):
        print(f"Rozpoznano callback trybu: {query.data}")
        mode_id = query.data[5:]  # Pobierz ID trybu (usuń prefix "mode_")
        await handle_mode_selection(update, context, mode_id)
        return

    # Obsługa tematów konwersacji
    if query.data.startswith("theme_") or query.data == "new_theme" or query.data == "no_theme":
        from handlers.theme_handler import handle_theme_callback
        await handle_theme_callback(update, context)
        return
    
    # POPRAWKA: Bezpośrednia obsługa history_view
    if query.data == "history_view":
        user_id = query.from_user.id
        language = get_user_language(context, user_id)
        
        # Pobierz aktywną konwersację
        from database.sqlite_client import get_active_conversation, get_conversation_history
        conversation = get_active_conversation(user_id)
        
        if not conversation:
            # Informacja przez wiadomość
            keyboard = [[InlineKeyboardButton(get_text("back", language), callback_data="menu_section_history")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(
                    caption=get_text("history_no_conversation", language),
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text(
                    text=get_text("history_no_conversation", language),
                    reply_markup=reply_markup
                )
            return
        
        # Pobierz historię konwersacji
        history = get_conversation_history(conversation['id'])
        
        if not history:
            keyboard = [[InlineKeyboardButton(get_text("back", language), callback_data="menu_section_history")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(
                    caption=get_text("history_empty", language),
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text(
                    text=get_text("history_empty", language),
                    reply_markup=reply_markup
                )
            return
        
        # Przygotuj tekst z historią - bez formatowania Markdown
        message_text = f"{get_text('history_title', language)}\n\n"
        
        for i, msg in enumerate(history[-10:]):  # Ostatnie 10 wiadomości
            sender = get_text("history_user", language) if msg['is_from_user'] else get_text("history_bot", language)
            
            # Skróć treść wiadomości
            content = msg['content']
            if len(content) > 100:
                content = content[:97] + "..."
                
            message_text += f"{i+1}. {sender}: {content}\n\n"
        
        # Dodaj przycisk do powrotu
        keyboard = [[InlineKeyboardButton(get_text("back", language), callback_data="menu_section_history")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if hasattr(query.message, 'caption'):
            await query.edit_message_caption(
                caption=message_text,
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text(
                text=message_text,
                reply_markup=reply_markup
            )
        return
    
# Poprawiona obsługa menu_credits_check
if query.data == "menu_credits_check" or query.data == "credits_check":
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Dodanie paska nawigacyjnego
    navigation_path = f"🏠 {get_text('menu', language, default='Menu główne')} > 💰 {get_text('menu_credits', language)} > 💳 {get_text('check_balance', language)}"
    
    # Pobierz aktualne dane kredytów
    credits = get_user_credits(user_id)
    credit_stats = get_user_credit_stats(user_id)
    
    # Generuj kolorowy pasek stanu kredytów
    from handlers.menu_handler import get_credit_status_bar
    credits_bar = get_credit_status_bar(credits)
    
    # Przygotuj tekst wiadomości z paskiem nawigacyjnym
    message = f"{navigation_path}\n\n"
    message += f"*{get_text('credits_management', language, default='Zarządzanie kredytami')}*\n\n"
    message += f"{get_text('current_balance', language)}: *{credits}* {get_text('credits', language)}\n"
    message += f"Stan kredytów: {credits_bar}\n\n"
    
    if 'total_purchased' in credit_stats:
        message += f"{get_text('total_purchased', language)}: *{credit_stats.get('total_purchased', 0)}* {get_text('credits', language)}\n"
    
    if 'total_spent' in credit_stats:
        message += f"{get_text('total_spent', language)}: *{credit_stats.get('total_spent', 0):.2f}* PLN\n"
    
    if 'last_purchase' in credit_stats and credit_stats['last_purchase']:
        formatted_date = credit_stats['last_purchase'].split('T')[0] if 'T' in credit_stats['last_purchase'] else credit_stats['last_purchase']
        message += f"{get_text('last_purchase', language)}: *{formatted_date}*\n"
    
    message += f"\n*{get_text('credit_history', language)} ({get_text('last_10', language, default='ostatnie 10')}):*\n"
    
    if credit_stats.get('usage_history'):
        for i, transaction in enumerate(credit_stats['usage_history'], 1):
            date = transaction['date'].split('T')[0] if 'T' in transaction['date'] else transaction['date']
            if transaction['type'] in ["add", "purchase"]:
                message += f"\n{i}. ➕ +{transaction['amount']} {get_text('credits', language)} ({date})"
            else:
                message += f"\n{i}. ➖ -{transaction['amount']} {get_text('credits', language)} ({date})"
            if transaction.get('description'):
                message += f" - {transaction['description']}"
    else:
        message += f"\n{get_text('no_transactions', language)}"
    
    # Klawiatura z opcjami
    keyboard = [
        [InlineKeyboardButton(get_text("buy_credits_btn", language), callback_data="menu_credits_buy")],
        [InlineKeyboardButton(get_text("credit_stats", language, default="Statystyki"), callback_data="credit_advanced_analytics")],
        [InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_section_credits"),
         InlineKeyboardButton("🏠", callback_data="menu_home")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Aktualizuj wiadomość
    try:
        if hasattr(query.message, 'caption'):
            await query.edit_message_caption(
                caption=message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        print(f"Błąd przy aktualizacji wiadomości: {e}")
        # Próbuj wysłać bez formatowania Markdown
        if hasattr(query.message, 'caption'):
            await query.edit_message_caption(
                caption=message,
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup
            )
    return True
    
    # Obsługa przycisku tłumaczenia zdjęcia
    if query.data.startswith("translate_photo_"):
        photo_file_id = query.data.replace("translate_photo_", "")
        user_id = query.from_user.id
        language = get_user_language(context, user_id)
        
        # Sprawdź, czy użytkownik ma wystarczającą liczbę kredytów
        credit_cost = CREDIT_COSTS["photo"]
        if not check_user_credits(user_id, credit_cost):
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(
                    caption=get_text("subscription_expired", language),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text(
                    text=get_text("subscription_expired", language),
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        # Pobierz zdjęcie
        try:
            if hasattr(query.message, 'caption'):
                message = await query.edit_message_caption(
                    caption="Tłumaczę tekst ze zdjęcia, proszę czekać...",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                message = await query.edit_message_text(
                    text="Tłumaczę tekst ze zdjęcia, proszę czekać...",
                    parse_mode=ParseMode.MARKDOWN
                )
            
            file = await context.bot.get_file(photo_file_id)
            file_bytes = await file.download_as_bytearray()
            
            # Tłumacz tekst ze zdjęcia
            translation = await analyze_image(file_bytes, f"photo_{photo_file_id}.jpg", mode="translate")
            
            # Odejmij kredyty
            deduct_user_credits(user_id, credit_cost, "Tłumaczenie tekstu ze zdjęcia")
            
            # Wyślij tłumaczenie
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(
                    caption=f"*Tłumaczenie tekstu ze zdjęcia:*\n\n{translation}",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text(
                    text=f"*Tłumaczenie tekstu ze zdjęcia:*\n\n{translation}",
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # Sprawdź aktualny stan kredytów
            credits = get_user_credits(user_id)
            if credits < 5:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"*{get_text('low_credits_warning', language)}* {get_text('low_credits_message', language, credits=credits)}",
                    parse_mode=ParseMode.MARKDOWN
                )
            
            return
        except Exception as e:
            print(f"Błąd przy tłumaczeniu zdjęcia: {e}")
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(
                    caption=f"Wystąpił błąd podczas tłumaczenia zdjęcia: {str(e)}",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text(
                    text=f"Wystąpił błąd podczas tłumaczenia zdjęcia: {str(e)}",
                    parse_mode=ParseMode.MARKDOWN
                )
            return
    
    # Obsługa przycisku tłumaczenia PDF
    if query.data.startswith("translate_pdf_"):
        document_file_id = query.data.replace("translate_pdf_", "")
        user_id = query.from_user.id
        language = get_user_language(context, user_id)
        
        # Sprawdź, czy użytkownik ma wystarczającą liczbę kredytów
        credit_cost = 8  # Koszt tłumaczenia PDF
        if not check_user_credits(user_id, credit_cost):
            await query.answer(get_text("subscription_expired_short", language, default="Niewystarczająca liczba kredytów."))
            
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(
                    caption=get_text("subscription_expired", language),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text(
                    text=get_text("subscription_expired", language),
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        # Pobierz plik
        try:
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(
                    caption=get_text("translating_pdf", language),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text(
                    text=get_text("translating_pdf", language),
                    parse_mode=ParseMode.MARKDOWN
                )
            
            file = await context.bot.get_file(document_file_id)
            file_bytes = await file.download_as_bytearray()
            
            # Tłumacz pierwszy akapit z PDF
            from utils.pdf_translator import translate_pdf_first_paragraph
            result = await translate_pdf_first_paragraph(file_bytes)
            
            # Odejmij kredyty
            deduct_user_credits(user_id, credit_cost, "Tłumaczenie pierwszego akapitu z PDF")
            
            # Przygotuj odpowiedź
            if result["success"]:
                response = f"*{get_text('pdf_translation_result', language)}*\n\n"
                response += f"*{get_text('original_text', language)}:*\n{result['original_text'][:500]}...\n\n"
                response += f"*{get_text('translated_text', language)}:*\n{result['translated_text'][:500]}..."
            else:
                response = f"*{get_text('pdf_translation_error', language)}*\n\n{result['error']}"
            
            # Wyślij wynik tłumaczenia
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(
                    caption=response,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text(
                    text=response,
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # Sprawdź aktualny stan kredytów
            credits = get_user_credits(user_id)
            if credits < 5:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"*{get_text('low_credits_warning', language)}* {get_text('low_credits_message', language, credits=credits)}",
                    parse_mode=ParseMode.MARKDOWN
                )
            
            return
        except Exception as e:
            print(f"Błąd przy tłumaczeniu PDF: {e}")
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(
                    caption=f"{get_text('pdf_translation_error', language)}: {str(e)}",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text(
                    text=f"{get_text('pdf_translation_error', language)}: {str(e)}",
                    parse_mode=ParseMode.MARKDOWN
                )
            return

    # Obsługa kredytów
    if query.data.startswith("buy_") or query.data.startswith("credits_"):
        from handlers.credit_handler import handle_credit_callback
        await handle_credit_callback(update, context)
        return
    
    # Obsługa historii
    if query.data.startswith("history_"):
        if query.data == "history_new":
            # Twórz nową konwersację
            conversation = create_new_conversation(user_id)
            # Sprawdź, czy wiadomość ma podpis (jest to zdjęcie lub inny typ mediów)
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(
                    caption=get_text("new_chat_success", get_user_language(context, user_id)),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text(
                    text=get_text("new_chat_success", get_user_language(context, user_id)),
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        elif query.data == "history_export":
            # Eksportuj bieżącą konwersację
            from handlers.export_handler import export_conversation
            # Tworzymy sztuczny obiekt update do przekazania do funkcji export_conversation
            class FakeUpdate:
                class FakeMessage:
                    def __init__(self, chat_id, message_id):
                        self.chat_id = chat_id
                        self.message_id = message_id
                        self.chat = type('obj', (object,), {'send_action': lambda *args, **kwargs: None})
                    async def reply_text(self, *args, **kwargs):
                        pass
                    async def reply_document(self, *args, **kwargs):
                        pass
                def __init__(self, query):
                    self.message = self.FakeMessage(query.message.chat_id, query.message.message_id)
                    self.effective_user = query.from_user
                    self.effective_chat = type('obj', (object,), {'id': query.message.chat_id})
            
            fake_update = FakeUpdate(query)
            await export_conversation(fake_update, context)
            # Informacja o eksporcie
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(
                    caption="Eksportowanie konwersacji do PDF...",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text(
                    text="Eksportowanie konwersacji do PDF...",
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        elif query.data == "history_delete":
            # Pytanie o potwierdzenie usunięcia historii
            keyboard = [
                [
                    InlineKeyboardButton(get_text("yes", get_user_language(context, user_id)), callback_data="history_confirm_delete"),
                    InlineKeyboardButton(get_text("no", get_user_language(context, user_id)), callback_data="menu_section_history")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(
                    caption=get_text("history_delete_confirm", get_user_language(context, user_id)),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text(
                    text=get_text("history_delete_confirm", get_user_language(context, user_id)),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            return
    
    # Obsługa przycisku restartu bota
    if query.data == "restart_bot":
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        language = get_user_language(context, user_id)
        
        restart_message = get_text("restarting_bot", language)
        try:
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(caption=restart_message)
            else:
                await query.edit_message_text(text=restart_message)
        except Exception as e:
            print(f"Błąd przy aktualizacji wiadomości: {e}")
        
        # Resetowanie konwersacji - tworzymy nową konwersację i czyścimy kontekst
        conversation = create_new_conversation(user_id)
        
        # Zachowujemy wybrane ustawienia użytkownika (język, model)
        user_data = {}
        if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
            # Pobieramy tylko podstawowe ustawienia, reszta jest resetowana
            old_user_data = context.chat_data['user_data'][user_id]
            if 'language' in old_user_data:
                user_data['language'] = old_user_data['language']
            if 'current_model' in old_user_data:
                user_data['current_model'] = old_user_data['current_model']
            if 'current_mode' in old_user_data:
                user_data['current_mode'] = old_user_data['current_mode']
        
        # Resetujemy dane użytkownika w kontekście i ustawiamy tylko zachowane ustawienia
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        context.chat_data['user_data'][user_id] = user_data
        
        # Potwierdź restart
        restart_complete = get_text("restart_command", language)
        
        # Utwórz klawiaturę menu
        keyboard = [
            [
                InlineKeyboardButton(get_text("menu_chat_mode", language), callback_data="menu_section_chat_modes"),
                InlineKeyboardButton(get_text("image_generate", language), callback_data="menu_image_generate")
            ],
            [
                InlineKeyboardButton(get_text("menu_credits", language), callback_data="menu_section_credits"),
                InlineKeyboardButton(get_text("menu_dialog_history", language), callback_data="menu_section_history")
            ],
            [
                InlineKeyboardButton(get_text("menu_settings", language), callback_data="menu_section_settings"),
                InlineKeyboardButton(get_text("menu_help", language), callback_data="menu_help")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Wyślij nową wiadomość z menu
        try:
            # Używamy welcome_message zamiast main_menu + status
            welcome_text = get_text("welcome_message", language, bot_name=BOT_NAME)
            message = await context.bot.send_message(
                chat_id=chat_id,
                text=restart_complete + "\n\n" + welcome_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Zapisz ID wiadomości menu i stan menu
            from handlers.menu_handler import store_menu_state
            store_menu_state(context, user_id, 'main', message.message_id)
        except Exception as e:
            print(f"Błąd przy wysyłaniu wiadomości po restarcie: {e}")
            # Próbuj wysłać prostą wiadomość
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=restart_complete
                )
            except Exception as e2:
                print(f"Nie udało się wysłać nawet prostej wiadomości: {e2}")
        
        return
        
    # Obsługa historii rozmów
    if query.data == "history_confirm_delete":
        user_id = query.from_user.id
        # Twórz nową konwersację (efektywnie "usuwając" historię)
        conversation = create_new_conversation(user_id)
        
        if conversation:
            from handlers.menu_handler import update_menu
            await update_menu(update, context, 'history')
        else:
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(
                    caption="Wystąpił błąd podczas czyszczenia historii.",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text(
                    text="Wystąpił błąd podczas czyszczenia historii.",
                    parse_mode=ParseMode.MARKDOWN
                )
        return
    
    # Obsługa notatek
    if query.data.startswith("note_"):
        from handlers.note_handler import handle_note_callback
        await handle_note_callback(update, context)
        return
    
    # Obsługa przypomnień  
    if query.data.startswith("reminder_"):
        from handlers.reminder_handler import handle_reminder_callback
        await handle_reminder_callback(update, context)
        return
    
    # Specjalna obsługa przycisku powrotu do głównego menu
    if query.data == "menu_back_main":
        keyboard = [
            [
                InlineKeyboardButton(get_text("menu_chat_mode", language), callback_data="menu_section_chat_modes"),
                InlineKeyboardButton(get_text("image_generate", language), callback_data="menu_image_generate")
            ],
            [
                InlineKeyboardButton(get_text("menu_credits", language), callback_data="menu_section_credits"),
                InlineKeyboardButton(get_text("menu_dialog_history", language), callback_data="menu_section_history")
            ],
            [
                InlineKeyboardButton(get_text("menu_settings", language), callback_data="menu_section_settings"),
                InlineKeyboardButton(get_text("menu_help", language), callback_data="menu_help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Używanie welcome_message
        welcome_text = get_text("welcome_message", language, bot_name=BOT_NAME)
        
        try:
            # Wyślij nową wiadomość zamiast edytować starą
            message = await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=welcome_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            # Zapisz ID nowej wiadomości menu
            store_menu_state(context, user_id, 'main', message.message_id)
            
            # Opcjonalnie usuń starą wiadomość
            try:
                await query.message.delete()
            except:
                pass
                
            return
        except Exception as e:
            print(f"Błąd przy obsłudze menu_back_main: {e}")
            # W przypadku błędu, kontynuujemy do standardowej obsługi

    # Jeśli dotarliśmy tutaj, oznacza to, że callback nie został obsłużony
    print(f"Nieobsłużony callback: {query.data}")
    try:
        if hasattr(query.message, 'caption'):
            await query.edit_message_caption(
                caption=f"Nieznany przycisk. Spróbuj ponownie później.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(
                text=f"Nieznany przycisk. Spróbuj ponownie później.",
                parse_mode=ParseMode.MARKDOWN
            )
    except:
        pass

async def handle_model_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, model_id):
    """Obsługa wyboru modelu AI"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy model istnieje
    if model_id not in AVAILABLE_MODELS:
        # Sprawdź typ wiadomości i użyj odpowiedniej metody
        if hasattr(query.message, 'caption'):
            await query.edit_message_caption(
                caption=get_text("model_not_available", language),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(
                text=get_text("model_not_available", language),
                parse_mode=ParseMode.MARKDOWN
            )
        return
    
    # Zapisz wybrany model w kontekście użytkownika
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    context.chat_data['user_data'][user_id]['current_model'] = model_id
    
    # Pobierz koszt kredytów dla wybranego modelu
    credit_cost = CREDIT_COSTS["message"].get(model_id, CREDIT_COSTS["message"]["default"])
    
    model_name = AVAILABLE_MODELS[model_id]
    
    message_text = get_text("model_selected", language, model=model_name, credits=credit_cost)
    
    # Sprawdź typ wiadomości i użyj odpowiedniej metody
    if hasattr(query.message, 'caption'):
        await query.edit_message_caption(
            caption=message_text,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await query.edit_message_text(
            text=message_text,
            parse_mode=ParseMode.MARKDOWN
        )

# Handlers dla komend administracyjnych

async def add_credits_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Dodaje kredyty użytkownikowi (tylko dla administratorów)
    Użycie: /addcredits [user_id] [ilość]
    """
    user_id = update.effective_user.id
    
    # Sprawdź, czy użytkownik jest administratorem
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("Nie masz uprawnień do tej komendy.")
        return
    
    # Sprawdź, czy podano argumenty
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Użycie: /addcredits [user_id] [ilość]")
        return
    
    try:
        target_user_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Błędne argumenty. Użycie: /addcredits [user_id] [ilość]")
        return
    
    # Sprawdź, czy ilość jest poprawna
    if amount <= 0 or amount > 10000:
        await update.message.reply_text("Ilość musi być liczbą dodatnią, nie większą niż 10000.")
        return
    
    # Dodaj kredyty
    success = add_user_credits(target_user_id, amount, "Dodano przez administratora")
    
    if success:
        # Pobierz aktualny stan kredytów
        credits = get_user_credits(target_user_id)
        await update.message.reply_text(
            f"Dodano *{amount}* kredytów użytkownikowi ID: *{target_user_id}*\n"
            f"Aktualny stan kredytów: *{credits}*",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text("Wystąpił błąd podczas dodawania kredytów.")

async def get_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Pobiera informacje o użytkowniku (tylko dla administratorów)
    Użycie: /userinfo [user_id]
    """
    user_id = update.effective_user.id
    
    # Sprawdź, czy użytkownik jest administratorem
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("Nie masz uprawnień do tej komendy.")
        return
    
    # Sprawdź, czy podano ID użytkownika
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Użycie: /userinfo [user_id]")
        return
    
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID użytkownika musi być liczbą.")
        return
    
    # Pobierz informacje o użytkowniku
    user = get_or_create_user(target_user_id)
    credits = get_user_credits(target_user_id)
    
    if not user:
        await update.message.reply_text("Użytkownik nie istnieje w bazie danych.")
        return
    
    # Formatuj dane
    subscription_end = user.get('subscription_end_date', 'Brak subskrypcji')
    if subscription_end and subscription_end != 'Brak subskrypcji':
        end_date = datetime.datetime.fromisoformat(subscription_end.replace('Z', '+00:00'))
        subscription_end = end_date.strftime('%d.%m.%Y %H:%M')
    
    info = f"""
*Informacje o użytkowniku:*
ID: `{user['id']}`
Nazwa użytkownika: {user.get('username', 'Brak')}
Imię: {user.get('first_name', 'Brak')}
Nazwisko: {user.get('last_name', 'Brak')}
Język: {user.get('language_code', 'Brak')}
Język interfejsu: {user.get('language', 'pl')}
Subskrypcja do: {subscription_end}
Aktywny: {'Tak' if user.get('is_active', False) else 'Nie'}
Data rejestracji: {user.get('created_at', 'Brak')}

*Status kredytów:*
Dostępne kredyty: *{credits}*
"""
    
    await update.message.reply_text(info, parse_mode=ParseMode.MARKDOWN)

# Główna funkcja uruchamiająca bota

def main():
    """Funkcja uruchamiająca bota"""
    # Inicjalizacja aplikacji
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Handler dla help
    application.add_handler(CommandHandler("help", help_command))

    # Handler dla setname
    application.add_handler(CommandHandler("setname", set_user_name))

    # Podstawowe komendy - USUNIĘTY handler removekeyboard
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", check_status))
    application.add_handler(CommandHandler("newchat", new_chat))
    application.add_handler(CommandHandler("models", show_models))
    application.add_handler(CommandHandler("mode", show_modes))
    application.add_handler(CommandHandler("image", generate_image))
    application.add_handler(CommandHandler("restart", restart_command))
    application.add_handler(CommandHandler("setname", set_user_name))
    application.add_handler(CommandHandler("language", language_command))

    # Handler dla help
    application.add_handler(CommandHandler("help", help_command))
    
    # Handler dla translate
    application.add_handler(CommandHandler("translate", translate_command))
    
    # Handler dla /status
    application.add_handler(CommandHandler("status", check_status))

    # Handler dla komendy /translate
    application.add_handler(CommandHandler("translate", translate_command))
    
    # Dodanie komendy onboarding
    application.add_handler(CommandHandler("onboarding", onboarding_command))
    
    # Handlery kodów aktywacyjnych
    application.add_handler(CommandHandler("code", code_command))
    application.add_handler(CommandHandler("gencode", admin_generate_code))
    
    # Handlery kredytów
    application.add_handler(CommandHandler("credits", credits_command))
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("creditstats", credit_stats_command))
    application.add_handler(CommandHandler("creditanalysis", credit_analytics_command))
    
    # Komendy administracyjne
    application.add_handler(CommandHandler("addcredits", add_credits_admin))
    application.add_handler(CommandHandler("userinfo", get_user_info))
    
    # Handler eksportu
    application.add_handler(CommandHandler("export", export_conversation))
    
    # Handlery tematów konwersacji
    application.add_handler(CommandHandler("theme", theme_command))
    application.add_handler(CommandHandler("notheme", notheme_command))
    
    # WAŻNE: Handler callbacków (musi być przed handlerami mediów i tekstu)
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Handlery mediów (dokumenty, zdjęcia)
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Handler wiadomości tekstowych (zawsze na końcu)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Uruchomienie bota
    application.run_polling()

if __name__ == '__main__':
    # Aktualizacja bazy danych przed uruchomieniem
    from update_database import run_all_updates
    run_all_updates()
    
    # Uruchomienie bota
    main()