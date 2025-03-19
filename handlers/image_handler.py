from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from config import CREDIT_COSTS, DALL_E_MODEL
from utils.translations import get_text
from handlers.menu_handler import get_user_language
from database.credits_client import check_user_credits, deduct_user_credits, get_user_credits
from utils.openai_client import generate_image_dall_e

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Generuje obraz za pomocą DALL-E na podstawie opisu
    Użycie: /image [opis obrazu]
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy użytkownik ma wystarczającą liczbę kredytów
    quality = "standard"  # domyślna jakość
    credit_cost = CREDIT_COSTS["image"][quality]
    
    # Pobierz aktualny stan kredytów
    current_credits = get_user_credits(user_id)
    
    if not check_user_credits(user_id, credit_cost):
        await update.message.reply_text(get_text("subscription_expired", language))
        return
    
    # Sprawdź, czy podano opis obrazu
    if not context.args or len(' '.join(context.args)) < 3:
        await update.message.reply_text(f"{get_text('image_usage', language, default='Użycie: /image [opis obrazu]')}\nNa przykład: /image pies na rowerze w parku")
        return
    
    prompt = ' '.join(context.args)
    
    # Dodaj ostrzeżenie dla operacji kosztujących > 5 kredytów
    if credit_cost > 5:
        from utils.warning_utils import create_credit_warning
        warning_msg, reply_markup, operation_id = create_credit_warning(credit_cost, current_credits, language)
        
        # Zapisz dane operacji w kontekście użytkownika
        if 'pending_operations' not in context.user_data:
            context.user_data['pending_operations'] = {}
        
        context.user_data['pending_operations'][operation_id] = {
            'type': 'generate_image',
            'prompt': prompt,
            'quality': quality,
            'cost': credit_cost
        }
        
        # Wyślij ostrzeżenie
        await update.message.reply_text(
            warning_msg,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Reszta oryginalnego kodu...
    # Powiadom użytkownika o rozpoczęciu generowania
    message = await update.message.reply_text(get_text("generating_image", language))
    
    # Wyślij informację o aktywności bota
    await update.message.chat.send_action(action=ChatAction.UPLOAD_PHOTO)
    
    # Generuj obraz
    image_url = await generate_image_dall_e(prompt)
    
    # Odejmij kredyty
    deduct_user_credits(user_id, credit_cost, "Generowanie obrazu")
    
    if image_url:
        # Usuń wiadomość o ładowaniu
        await message.delete()
        
        # Wyślij obraz
        await update.message.reply_photo(
            photo=image_url,
            caption=f"*{get_text('generated_image', language, default='Wygenerowany obraz:')}*\n{prompt}\n{get_text('cost', language, default='Koszt')}: {credit_cost} {get_text('credits', language, default='kredytów')}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # Aktualizuj wiadomość o błędzie
        await message.edit_text(get_text("image_generation_error", language, default="Przepraszam, wystąpił błąd podczas generowania obrazu. Spróbuj ponownie z innym opisem."))
    
    # Sprawdź aktualny stan kredytów
    credits = get_user_credits(user_id)
    if credits < 5:
        await update.message.reply_text(
            f"*{get_text('low_credits_warning', language, default='Uwaga:')}* {get_text('low_credits_message', language, default=f'Pozostało Ci tylko *{credits}* kredytów. Kup więcej za pomocą komendy /buy.', credits=credits)}",
            parse_mode=ParseMode.MARKDOWN
        )