from supabase import create_client
import uuid
import datetime
import pytz
import logging
from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

# Inicjalizacja klienta Supabase
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    logger.error(f"Błąd inicjalizacji klienta Supabase: {e}")
    # Fallback - możemy utworzyć pustą klasę, która nie rzuci błędu
    class DummyClient:
        def table(self, *args, **kwargs):
            return self
        def select(self, *args, **kwargs):
            return self
        def insert(self, *args, **kwargs):
            return self
        def update(self, *args, **kwargs):
            return self
        def eq(self, *args, **kwargs):
            return self
        def order(self, *args, **kwargs):
            return self
        def limit(self, *args, **kwargs):
            return self
        def execute(self, *args, **kwargs):
            logger.warning("Używanie dummy klienta Supabase - brak połączenia z bazą danych")
            return type('obj', (object,), {'data': []})
    
    supabase = DummyClient()

def get_or_create_user(user_id, username=None, first_name=None, last_name=None, language_code=None):
    """Pobierz lub utwórz użytkownika w bazie danych"""
    try:
        # Sprawdzamy czy użytkownik już istnieje
        response = supabase.table('users').select('*').eq('id', user_id).execute()
        
        if response.data:
            return response.data[0]
        
        # Jeśli nie istnieje, tworzymy nowego
        user_data = {
            'id': user_id,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'language_code': language_code,
            'created_at': datetime.datetime.now(pytz.UTC).isoformat(),
            'is_active': True
        }
        
        response = supabase.table('users').insert(user_data).execute()
        
        if response.data:
            return response.data[0]
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu/tworzeniu użytkownika: {e}")
    
    return None

def check_active_subscription(user_id):
    """Sprawdź czy użytkownik ma aktywną subskrypcję"""
    try:
        now = datetime.datetime.now(pytz.UTC).isoformat()
        
        response = supabase.table('users') \
            .select('subscription_end_date') \
            .eq('id', user_id) \
            .execute()
        
        if not response.data:
            return False
        
        user = response.data[0]
        end_date = user.get('subscription_end_date')
        
        if not end_date:
            return False
        
        # Konwertujemy string na datę
        end_date = datetime.datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        now = datetime.datetime.now(pytz.UTC)
        
        return end_date > now
    except Exception as e:
        logger.error(f"Błąd przy sprawdzaniu subskrypcji: {e}")
        return False

def get_subscription_end_date(user_id):
    """Pobierz datę końca subskrypcji użytkownika"""
    try:
        response = supabase.table('users') \
            .select('subscription_end_date') \
            .eq('id', user_id) \
            .execute()
        
        if not response.data or not response.data[0].get('subscription_end_date'):
            return None
        
        end_date = response.data[0].get('subscription_end_date')
        
        # Konwertujemy string na datę
        return datetime.datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu daty końca subskrypcji: {e}")
        return None

def activate_user_license(user_id, license_key):
    """Aktywuj licencję dla użytkownika"""
    try:
        # Pobierz licencję
        response = supabase.table('licenses') \
            .select('*') \
            .eq('license_key', license_key) \
            .eq('is_used', False) \
            .execute()
        
        if not response.data:
            return False, None
        
        license_data = response.data[0]
        
        # Oblicz datę końca subskrypcji
        now = datetime.datetime.now(pytz.UTC)
        end_date = now + datetime.timedelta(days=license_data['duration_days'])
        
        # Aktualizuj licencję
        supabase.table('licenses') \
            .update({
                'is_used': True,
                'used_at': now.isoformat(),
                'used_by': user_id
            }) \
            .eq('id', license_data['id']) \
            .execute()
        
        # Aktualizuj datę końca subskrypcji użytkownika
        supabase.table('users') \
            .update({'subscription_end_date': end_date.isoformat()}) \
            .eq('id', user_id) \
            .execute()
        
        return True, end_date
    except Exception as e:
        logger.error(f"Błąd przy aktywacji licencji: {e}")
        return False, None

def create_license(duration_days, price):
    """Utwórz nową licencję"""
    try:
        license_key = str(uuid.uuid4())
        
        license_data = {
            'license_key': license_key,
            'duration_days': duration_days,
            'price': price,
            'created_at': datetime.datetime.now(pytz.UTC).isoformat()
        }
        
        response = supabase.table('licenses').insert(license_data).execute()
        
        if response.data:
            return response.data[0]
    except Exception as e:
        logger.error(f"Błąd przy tworzeniu licencji: {e}")
    
    return None

def create_new_conversation(user_id):
    """Utwórz nową konwersację dla użytkownika"""
    try:
        conversation_data = {
            'user_id': user_id,
            'created_at': datetime.datetime.now(pytz.UTC).isoformat(),
            'last_message_at': datetime.datetime.now(pytz.UTC).isoformat()
        }
        
        response = supabase.table('conversations').insert(conversation_data).execute()
        
        if response.data:
            return response.data[0]
    except Exception as e:
        logger.error(f"Błąd przy tworzeniu nowej konwersacji: {e}")
    
    return None

def get_active_conversation(user_id):
    """Pobierz aktywną konwersację użytkownika (ostatnią)"""
    try:
        response = supabase.table('conversations') \
            .select('*') \
            .eq('user_id', user_id) \
            .order('last_message_at', desc=True) \
            .limit(1) \
            .execute()
        
        if response.data:
            return response.data[0]
        
        # Jeśli nie ma żadnej konwersacji, utwórz nową
        return create_new_conversation(user_id)
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu aktywnej konwersacji: {e}")
        return create_new_conversation(user_id)

def save_message(conversation_id, user_id, content, is_from_user, model_used=None):
    """Zapisz wiadomość w bazie danych"""
    try:
        message_data = {
            'conversation_id': conversation_id,
            'user_id': user_id,
            'content': content,
            'is_from_user': is_from_user,
            'created_at': datetime.datetime.now(pytz.UTC).isoformat(),
            'model_used': model_used
        }
        
        response = supabase.table('messages').insert(message_data).execute()
        
        if response.data:
            return response.data[0]
    except Exception as e:
        logger.error(f"Błąd przy zapisywaniu wiadomości: {e}")
    
    return None

def get_conversation_history(conversation_id, limit=20):
    """Pobierz historię konwersacji"""
    try:
        response = supabase.table('messages') \
            .select('*') \
            .eq('conversation_id', conversation_id) \
            .order('created_at', desc=False) \
            .limit(limit) \
            .execute()
        
        return response.data
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu historii konwersacji: {e}")
        return []

def save_prompt_template(name, description, prompt_text):
    """Zapisz szablon prompta w bazie danych"""
    try:
        template_data = {
            'name': name,
            'description': description,
            'prompt_text': prompt_text,
            'created_at': datetime.datetime.now(pytz.UTC).isoformat(),
            'is_active': True
        }
        
        response = supabase.table('prompt_templates').insert(template_data).execute()
        
        if response.data:
            return response.data[0]
    except Exception as e:
        logger.error(f"Błąd przy zapisywaniu szablonu prompta: {e}")
    
    return None

def get_prompt_templates():
    """Pobierz wszystkie aktywne szablony promptów"""
    try:
        response = supabase.table('prompt_templates') \
            .select('*') \
            .eq('is_active', True) \
            .execute()
        
        return response.data
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu szablonów promptów: {e}")
        return []

def get_prompt_template_by_id(template_id):
    """Pobierz szablon prompta po ID"""
    try:
        response = supabase.table('prompt_templates') \
            .select('*') \
            .eq('id', template_id) \
            .execute()
        
        if response.data:
            return response.data[0]
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu szablonu prompta: {e}")
    
    return None