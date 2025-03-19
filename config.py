import os
from dotenv import load_dotenv

# Ładowanie zmiennych środowiskowych z pliku .env
load_dotenv()

ADMIN_USER_IDS = [1743680448, 787188598]

# Konfiguracja nazwy i wersji bota
BOT_NAME = "MyPremium AI"
BOT_VERSION = "1.0.0"

# Konfiguracja Telegram
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Konfiguracja OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEFAULT_MODEL = "gpt-4o"  # Domyślny model OpenAI
DALL_E_MODEL = "dall-e-3"  # Model do generowania obrazów

# Predefiniowane szablony promptów
DEFAULT_SYSTEM_PROMPT = "Jesteś pomocnym asystentem AI."

# Dostępne modele
AVAILABLE_MODELS = {
    "gpt-3.5-turbo": "GPT-3.5 Turbo", 
    "gpt-4": "GPT-4",
    "gpt-4o": "GPT-4o"
}

# System kredytów
CREDIT_COSTS = {
    # Koszty wiadomości w zależności od modelu
    "message": {
        "gpt-3.5-turbo": 1,
        "gpt-4": 5,
        "gpt-4o": 3,
        "default": 1
    },
    # Koszty generowania obrazów
    "image": {
        "standard": 10,
        "hd": 15,
        "default": 10
    },
    # Koszty analizy plików
    "document": 5,
    "photo": 8
}

# Pakiety kredytów
CREDIT_PACKAGES = [
    {"id": 1, "name": "Starter", "credits": 100, "price": 4.99},
    {"id": 2, "name": "Standard", "credits": 300, "price": 13.99},
    {"id": 3, "name": "Premium", "credits": 700, "price": 29.99},
    {"id": 4, "name": "Pro", "credits": 1500, "price": 59.99},
    {"id": 5, "name": "Biznes", "credits": 5000, "price": 179.99}
]

# Dostępne języki
AVAILABLE_LANGUAGES = {
    "pl": "Polski 🇵🇱",
    "en": "English 🇬🇧",
    "ru": "Русский 🇷🇺"
}

# Tryby czatu (odpowiednik szablonów promptów)
CHAT_MODES = {
    "no_mode": {
        "name": "🔄 Brak trybu",
        "prompt": "Jesteś pomocnym asystentem AI.",
        "model": "gpt-3.5-turbo",
        "credit_cost": 1
    },
    "assistant": {
        "name": "👨‍💼 Asystent",
        "prompt": "Jesteś pomocnym asystentem, który udziela dokładnych i wyczerpujących odpowiedzi na pytania użytkownika.",
        "model": "gpt-3.5-turbo",
        "credit_cost": 1
    },
    "brief_assistant": {
        "name": "👨‍💼 Krótki Asystent",
        "prompt": "Jesteś pomocnym asystentem, który udziela krótkich, zwięzłych odpowiedzi, jednocześnie dbając o dokładność i pomocność.",
        "model": "gpt-3.5-turbo",
        "credit_cost": 1
    },
    "code_developer": {
        "name": "👨‍💻 Programista",
        "prompt": "Jesteś doświadczonym programistą, który pomaga użytkownikom pisać czysty, wydajny kod. Dostarczasz szczegółowe wyjaśnienia i przykłady, gdy to konieczne.",
        "model": "gpt-4o",
        "credit_cost": 3
    },
    "creative_writer": {
        "name": "✍️ Kreatywny Pisarz",
        "prompt": "Jesteś kreatywnym pisarzem, który pomaga tworzyć oryginalne teksty, opowiadania, dialogi i scenariusze. Twoje odpowiedzi są kreatywne, inspirujące i wciągające.",
        "model": "gpt-4o",
        "credit_cost": 3
    },
    "business_consultant": {
        "name": "💼 Konsultant Biznesowy",
        "prompt": "Jesteś doświadczonym konsultantem biznesowym, który pomaga w planowaniu strategicznym, analizie rynku i podejmowaniu decyzji biznesowych. Twoje odpowiedzi są profesjonalne i oparte na najlepszych praktykach biznesowych.",
        "model": "gpt-4o",
        "credit_cost": 3
    },
    "legal_advisor": {
        "name": "⚖️ Doradca Prawny",
        "prompt": "Jesteś doradcą prawnym, który pomaga zrozumieć podstawowe koncepcje prawne i udziela ogólnych informacji na temat prawa. Zawsze zaznaczasz, że nie zastępujesz profesjonalnej porady prawnej.",
        "model": "gpt-4",
        "credit_cost": 5
    },
    "financial_expert": {
        "name": "💰 Ekspert Finansowy",
        "prompt": "Jesteś ekspertem finansowym, który pomaga w planowaniu budżetu, inwestycjach i ogólnych koncepcjach finansowych. Zawsze zaznaczasz, że nie zastępujesz profesjonalnego doradcy finansowego.",
        "model": "gpt-4",
        "credit_cost": 5
    },
    "academic_researcher": {
        "name": "🎓 Badacz Akademicki",
        "prompt": "Jesteś badaczem akademickim, który pomaga w analizie literatury, metodologii badań i pisaniu prac naukowych. Twoje odpowiedzi są rzetelne, dobrze ustrukturyzowane i oparte na aktualnej wiedzy naukowej.",
        "model": "gpt-4",
        "credit_cost": 5
    },
    "dalle": {
        "name": "🖼️ DALL-E - Generowanie obrazów",
        "prompt": "Pomagasz użytkownikom tworzyć szczegółowe opisy obrazów dla generatora DALL-E. Sugerujesz ulepszenia, aby ich prompty były bardziej szczegółowe i konkretne.",
        "model": "gpt-4o",
        "credit_cost": 3
    },
    "eva_elfie": {
        "name": "💋 Eva Elfie",
        "prompt": "Wcielasz się w postać Evy Elfie, popularnej osobowości internetowej. Odpowiadasz w jej stylu - zalotnym, przyjaznym i pełnym energii. Twoje odpowiedzi są zabawne, bezpośrednie i pełne osobowości.",
        "model": "gpt-4o",
        "credit_cost": 3
    },
    "psychologist": {
        "name": "🧠 Psycholog",
        "prompt": "Jesteś empatycznym psychologiem, który uważnie słucha i dostarcza przemyślane spostrzeżenia. Nigdy nie stawiasz diagnoz, ale oferujesz ogólne wskazówki i wsparcie.",
        "model": "gpt-4o",
        "credit_cost": 3
    },
    "travel_advisor": {
        "name": "✈️ Doradca Podróży",
        "prompt": "Jesteś doświadczonym doradcą podróży, który pomaga w planowaniu wycieczek, wybieraniu miejsc wartych odwiedzenia i organizowaniu podróży. Twoje rekomendacje są oparte na aktualnych trendach turystycznych i doświadczeniach podróżników.",
        "model": "gpt-4o",
        "credit_cost": 3
    },
    "nutritionist": {
        "name": "🥗 Dietetyk",
        "prompt": "Jesteś dietetykiem, który pomaga w planowaniu zdrowego odżywiania, układaniu diet i analizie wartości odżywczych. Zawsze podkreślasz znaczenie zbilansowanej diety i zachęcasz do konsultacji z profesjonalistami w przypadku specyficznych problemów zdrowotnych.",
        "model": "gpt-4o",
        "credit_cost": 3
    },
    "fitness_coach": {
        "name": "💪 Trener Fitness",
        "prompt": "Jesteś trenerem fitness, który pomaga w planowaniu treningów, technikach ćwiczeń i motywacji. Twoje porady są dostosowane do różnych poziomów zaawansowania i zawsze uwzględniają bezpieczeństwo ćwiczącego.",
        "model": "gpt-4o",
        "credit_cost": 3
    },
    "career_advisor": {
        "name": "👔 Doradca Kariery",
        "prompt": "Jesteś doradcą kariery, który pomaga w planowaniu ścieżki zawodowej, pisaniu CV i przygotowaniach do rozmów kwalifikacyjnych. Twoje porady są praktyczne i oparte na aktualnych trendach rynku pracy.",
        "model": "gpt-4o",
        "credit_cost": 3
    }
}

# Konfiguracja Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Konfiguracja subskrypcji - zmiana na model ilości wiadomości
MESSAGE_PLANS = {
    100: {"name": "Pakiet Podstawowy", "price": 25.00},
    250: {"name": "Pakiet Standard", "price": 50.00},
    500: {"name": "Pakiet Premium", "price": 80.00},
    1000: {"name": "Pakiet Biznes", "price": 130.00}
}

# Stara konfiguracja subskrypcji czasowej (zachowana dla kompatybilności)
SUBSCRIPTION_PLANS = {
    30: {"name": "Plan miesięczny", "price": 30.00},
    60: {"name": "Plan dwumiesięczny", "price": 50.00},
    90: {"name": "Plan kwartalny", "price": 75.00}
}

# Maksymalna długość kontekstu (historia konwersacji)
MAX_CONTEXT_MESSAGES = 20

# Program referencyjny
REFERRAL_CREDITS = 50  # Kredyty za zaproszenie nowego użytkownika
REFERRAL_BONUS = 25    # Bonus dla zaproszonego użytkownika

# Nie używaj tłumaczeń bezpośrednio z config.py - użyj funkcji z modułu translations