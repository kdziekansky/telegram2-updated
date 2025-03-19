from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from config import SUBSCRIPTION_EXPIRED_MESSAGE
from database.supabase_client import check_active_subscription
from utils.openai_client import analyze_document, analyze_image

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy użytkownik ma wystarczającą liczbę kredytów
    credit_cost = CREDIT_COSTS["document"]
    current_credits = get_user_credits(user_id)
    
    # Dodaj ostrzeżenie dla operacji kosztujących > 5 kredytów
    if credit_cost > 5:
        from utils.warning_utils import create_credit_warning
        warning_msg, reply_markup, operation_id = create_credit_warning(credit_cost, current_credits, language)
        
        # Zapisz dane operacji w kontekście użytkownika
        if 'pending_operations' not in context.user_data:
            context.user_data['pending_operations'] = {}
        
        document = update.message.document
        file_name = document.file_name
        
        context.user_data['pending_operations'][operation_id] = {
            'type': 'analyze_document',
            'document_id': document.file_id,
            'file_name': file_name,
            'cost': credit_cost
        }
        
        # Wyślij ostrzeżenie
        await update.message.reply_text(
            warning_msg,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Sprawdź rozmiar pliku (limit 25MB)
    if document.file_size > 25 * 1024 * 1024:
        await update.message.reply_text("Plik jest zbyt duży. Maksymalny rozmiar to 25MB.")
        return
    
    # Pobierz plik
    message = await update.message.reply_text("Analizuję plik, proszę czekać...")
    
    # Wyślij informację o aktywności bota
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    file = await context.bot.get_file(document.file_id)
    file_bytes = await file.download_as_bytearray()
    
    # Analizuj plik
    analysis = analyze_document(file_bytes, file_name)
    
    # Wyślij analizę do użytkownika
    await message.edit_text(
        f"*Analiza pliku:* {file_name}\n\n{analysis}",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa przesłanych zdjęć"""
    user_id = update.effective_user.id
    
    # Sprawdź, czy użytkownik ma aktywną subskrypcję
    if not check_active_subscription(user_id):
        await update.message.reply_text(SUBSCRIPTION_EXPIRED_MESSAGE)
        return
    
    # Wybierz zdjęcie o najwyższej rozdzielczości
    photo = update.message.photo[-1]
    
    # Pobierz zdjęcie
    message = await update.message.reply_text("Analizuję zdjęcie, proszę czekać...")
    
    # Wyślij informację o aktywności bota
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    file = await context.bot.get_file(photo.file_id)
    file_bytes = await file.download_as_bytearray()
    
    # Analizuj zdjęcie
    analysis = analyze_image(file_bytes, f"photo_{photo.file_unique_id}.jpg")
    
    # Wyślij analizę do użytkownika
    await message.edit_text(
        f"*Analiza zdjęcia:*\n\n{analysis}",
        parse_mode=ParseMode.MARKDOWN
    )