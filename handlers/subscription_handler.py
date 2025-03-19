from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import LICENSE_ACTIVATED_MESSAGE, INVALID_LICENSE_MESSAGE, SUBSCRIPTION_EXPIRED_MESSAGE
from database.supabase_client import activate_user_license, check_active_subscription, get_subscription_end_date

async def activate_license(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Aktywuje licencję dla użytkownika
    Użycie: /activate [klucz_licencyjny]
    """
    user_id = update.effective_user.id
    
    # Sprawdź, czy podano klucz licencyjny
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Użycie: /activate [klucz_licencyjny]")
        return
    
    license_key = context.args[0]
    
    # Aktywuj licencję
    success, end_date = activate_user_license(user_id, license_key)
    
    if success and end_date:
        formatted_date = end_date.strftime('%d.%m.%Y %H:%M')
        message = LICENSE_ACTIVATED_MESSAGE.format(end_date=formatted_date)
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(INVALID_LICENSE_MESSAGE)

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sprawdza status subskrypcji użytkownika
    Użycie: /status
    """
    user_id = update.effective_user.id
    
    # Sprawdź, czy użytkownik ma aktywną subskrypcję
    if check_active_subscription(user_id):
        end_date = get_subscription_end_date(user_id)
        formatted_date = end_date.strftime('%d.%m.%Y %H:%M')
        
        message = f"Twoja subskrypcja jest aktywna.\nData wygaśnięcia: *{formatted_date}*"
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(SUBSCRIPTION_EXPIRED_MESSAGE)