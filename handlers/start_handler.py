from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import BOT_NAME, AVAILABLE_LANGUAGES
from utils.translations import get_text
from database.sqlite_client import get_or_create_user, get_message_status
from database.credits_client import get_user_credits

# Zabezpieczony import z awaryjnym fallbackiem
try:
    from utils.referral import use_referral_code
except ImportError:
    # Fallback jeśli import nie zadziała
    def use_referral_code(user_id, code):
        """
        Prosta implementacja awaryjnego fallbacku dla use_referral_code
        """
        # Jeśli kod ma format REF123, wyodrębnij ID polecającego
        if code.startswith("REF") and code[3:].isdigit():
            referrer_id = int(code[3:])
            # Sprawdź, czy użytkownik nie używa własnego kodu
            if referrer_id == user_id:
                return False, None
            # Dodanie kredytów zostałoby implementowane tutaj w prawdziwym przypadku
            return True, referrer_id
        return False, None

def get_user_language(context, user_id):
    """
    Pobiera język użytkownika z kontekstu lub bazy danych
    
    Args:
        context: Kontekst bota
        user_id: ID użytkownika
        
    Returns:
        str: Kod języka (pl, en, ru)
    """
    # Sprawdź, czy język jest zapisany w kontekście
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data'] and 'language' in context.chat_data['user_data'][user_id]:
        return context.chat_data['user_data'][user_id]['language']
    
    # Jeśli nie, pobierz z bazy danych
    try:
        from database.sqlite_client import sqlite3, DB_PATH
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT language FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            # Zapisz w kontekście na przyszłość
            if 'user_data' not in context.chat_data:
                context.chat_data['user_data'] = {}
            
            if user_id not in context.chat_data['user_data']:
                context.chat_data['user_data'][user_id] = {}
            
            context.chat_data['user_data'][user_id]['language'] = result[0]
            return result[0]
    except Exception as e:
        print(f"Błąd pobierania języka z bazy: {e}")
    
    # Sprawdź language_code, jeśli nie znaleziono language
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT language_code FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                # Zapisz w kontekście na przyszłość
                if 'user_data' not in context.chat_data:
                    context.chat_data['user_data'] = {}
                
                if user_id not in context.chat_data['user_data']:
                    context.chat_data['user_data'][user_id] = {}
                
                context.chat_data['user_data'][user_id]['language'] = result[0]
                return result[0]
        except Exception as e:
            print(f"Błąd pobierania language_code z bazy: {e}")
        
        # Domyślny język, jeśli wszystkie metody zawiodły
        return "pl"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługa komendy /start
    Wyświetla wybór języka lub banner graficzny i wiadomość powitalną z menu
    """
    try:
        user = update.effective_user
        
        # Sprawdź, czy użytkownik istnieje w bazie
        user_data = get_or_create_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code
        )
        
        # Zawsze pokazuj wybór języka przy starcie
        await show_language_selection(update, context)
        
    except Exception as e:
        print(f"Błąd w funkcji start_command: {e}")
        import traceback
        traceback.print_exc()
        
        language = "pl"  # Domyślny język w przypadku błędu
        await update.message.reply_text(
            get_text("initialization_error", language, default="Wystąpił błąd podczas inicjalizacji bota. Spróbuj ponownie później.")
        )

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługa komendy /language
    Wyświetla tylko ekran wyboru języka
    """
    return await show_language_selection(update, context)

async def show_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Wyświetla wybór języka przy pierwszym uruchomieniu ze zdjęciem
    """
    try:
        # Utwórz przyciski dla każdego języka
        keyboard = []
        for lang_code, lang_name in AVAILABLE_LANGUAGES.items():
            keyboard.append([InlineKeyboardButton(lang_name, callback_data=f"start_lang_{lang_code}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Link do zdjęcia bannera
        banner_url = "https://i.imgur.com/T3iJJlI.png"
        
        # Użyj neutralnego języka dla pierwszej wiadomości
        language_message = f"Wybierz język / Choose language / Выберите язык:"
        
        # Wyślij zdjęcie z tekstem wyboru języka
        await update.message.reply_photo(
            photo=banner_url,
            caption=language_message,
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Błąd w funkcji show_language_selection: {e}")
        import traceback
        traceback.print_exc()
        
        await update.message.reply_text(
            "Wystąpił błąd podczas wyboru języka. Spróbuj ponownie później."
        )

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługuje wybór języka przez użytkownika
    """
    try:
        query = update.callback_query
        await query.answer()
        
        if not query.data.startswith("start_lang_"):
            return
        
        language = query.data[11:]  # Usuń prefix "start_lang_"
        user_id = query.from_user.id
        
        # Zapisz język w bazie danych - używamy nowej funkcji
        try:
            from database.sqlite_client import update_user_language
            update_user_language(user_id, language)
        except Exception as e:
            print(f"Błąd zapisywania języka: {e}")
        
        # Zapisz język w kontekście
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        
        if user_id not in context.chat_data['user_data']:
            context.chat_data['user_data'][user_id] = {}
        
        context.chat_data['user_data'][user_id]['language'] = language
        
        # Teraz wszystkie pobierane teksty będą używać nowego języka
        
        # Link do zdjęcia bannera
        banner_url = "https://i.imgur.com/OiPImmC.png"
        
        # Pobierz przetłumaczony tekst powitalny
        welcome_text = get_text("welcome_message", language, bot_name=BOT_NAME)
        
        # Utwórz klawiaturę menu z przetłumaczonymi tekstami
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
        
        # Aktualizuj wiadomość
        try:
            await query.edit_message_caption(
                caption=welcome_text,
                reply_markup=reply_markup
            )
            
            # Zapisz ID wiadomości menu i stan menu
            from handlers.menu_handler import store_menu_state
            store_menu_state(context, user_id, 'main', query.message.message_id)
        except Exception as e:
            print(f"Błąd przy aktualizacji podpisu wiadomości: {e}")
            try:
                # Jeśli nie możemy edytować, to spróbujmy wysłać nową wiadomość
                message = await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=welcome_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Zapisz ID wiadomości menu i stan menu
                from handlers.menu_handler import store_menu_state
                store_menu_state(context, user_id, 'main', message.message_id)
            except Exception as e2:
                print(f"Błąd przy wysyłaniu nowej wiadomości: {e2}")
    except Exception as e:
        print(f"Błąd w funkcji handle_language_selection: {e}")

async def show_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=None, language=None):
    """
    Wyświetla wiadomość powitalną z menu jako zdjęcie z podpisem
    """
    try:
        if not user_id:
            user_id = update.effective_user.id
            
        if not language:
            language = get_user_language(context, user_id)
            if not language:
                language = "pl"  # Domyślny język
        
        # Zapisz język w kontekście
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        
        if user_id not in context.chat_data['user_data']:
            context.chat_data['user_data'][user_id] = {}
        
        context.chat_data['user_data'][user_id]['language'] = language
        
        # Pobierz stan kredytów
        credits = get_user_credits(user_id)
        
        # Link do zdjęcia bannera
        banner_url = "https://i.imgur.com/YPubLDE.png"
        
        # Pobierz przetłumaczony tekst powitalny
        welcome_text = get_text("welcome_message", language, bot_name=BOT_NAME)
        
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
        
        # Wyślij zdjęcie z podpisem i menu
        message = await update.message.reply_photo(
            photo=banner_url,
            caption=welcome_text,
            reply_markup=reply_markup
        )
        
        # Zapisz ID wiadomości menu i stan menu
        from handlers.menu_handler import store_menu_state
        store_menu_state(context, user_id, 'main', message.message_id)
        
        return message
    except Exception as e:
        print(f"Błąd w funkcji show_welcome_message: {e}")
        # Fallback do tekstu w przypadku błędu
        await update.message.reply_text(
            "Wystąpił błąd podczas wyświetlania wiadomości powitalnej. Spróbuj ponownie później."
        )
        return None