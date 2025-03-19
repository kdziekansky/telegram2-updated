#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Skrypt naprawiający problemy z tłumaczeniami w bocie.
Ten skrypt dokonuje poprawek w następujących plikach:
1. utils/openai_client.py - usunięcie hardkodowanych tekstów
2. handlers/translate_handler.py - poprawienie funkcji tłumaczenia
3. helpers/help_handler.py - naprawienie tekstu pomocy
"""

import os
import re

def fix_openai_client():
    """Naprawia hardkodowane teksty w openai_client.py"""
    print("Naprawianie pliku utils/openai_client.py...")
    
    file_path = "utils/openai_client.py"
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Usuwamy zduplikowaną funkcję analyze_document bez target_language
    pattern = r"async def analyze_document\(file_content, file_name, mode=\"analyze\"\):.*?return f\"Przepraszam, wystąpił błąd podczas analizy dokumentu: {str\(e\)}\""
    content = re.sub(pattern, "", content, flags=re.DOTALL)
    
    # Poprawiamy funkcje aby używały get_text zamiast hardkodowanych tekstów
    analyze_image_modified = '''
async def analyze_image(image_content, image_name, mode="analyze", target_language="en"):
    """
    Analizuj obraz za pomocą OpenAI API
    
    Args:
        image_content (bytes): Zawartość obrazu
        image_name (str): Nazwa obrazu
        mode (str): Tryb analizy: "analyze" (domyślnie) lub "translate"
        target_language (str): Docelowy język tłumaczenia (dwuliterowy kod)
        
    Returns:
        str: Analiza obrazu lub tłumaczenie tekstu
    """
    try:
        # Kodowanie obrazu do Base64
        base64_image = base64.b64encode(image_content).decode('utf-8')
        
        # Przygotuj odpowiednie instrukcje bazując na trybie
        if mode == "translate":
            language_names = {
                "en": "English",
                "pl": "Polish",
                "ru": "Russian",
                "fr": "French",
                "de": "German",
                "es": "Spanish",
                "it": "Italian",
                "zh": "Chinese"
            }
            target_lang_name = language_names.get(target_language, target_language)
            
            # Uniwersalne instrukcje niezależne od języka
            system_instruction = f"You are a helpful assistant who translates text from images to {target_lang_name}. Focus only on reading and translating the text visible in the image."
            user_instruction = f"Read all text visible in the image and translate it to {target_lang_name}. Provide only the translation, without additional explanations."
        else:  # tryb analyze
            system_instruction = "You are a helpful assistant who analyzes images. Your answers should be detailed but concise."
            user_instruction = "Describe this image. What do you see? Provide a detailed but concise analysis of the image content."
        
        messages = [
            {
                "role": "system", 
                "content": system_instruction
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_instruction
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
        
        response = await client.chat.completions.create(
            model="gpt-4o",  # Używamy GPT-4o zamiast zdeprecjonowanego gpt-4-vision-preview
            messages=messages,
            max_tokens=800  # Zwiększona liczba tokenów dla dłuższych tekstów
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Błąd analizy obrazu: {e}")
        return f"Sorry, an error occurred while analyzing the image: {str(e)}"
'''

    analyze_document_modified = '''
async def analyze_document(file_content, file_name, mode="analyze", target_language="en"):
    """
    Analizuj lub tłumacz dokument za pomocą OpenAI API
    
    Args:
        file_content (bytes): Zawartość pliku
        file_name (str): Nazwa pliku
        mode (str): Tryb analizy: "analyze" (domyślnie) lub "translate"
        target_language (str): Docelowy język tłumaczenia (dwuliterowy kod)
        
    Returns:
        str: Analiza dokumentu, tłumaczenie lub informacja o błędzie
    """
    try:
        # Określamy typ zawartości na podstawie rozszerzenia pliku
        file_extension = os.path.splitext(file_name)[1].lower()
        
        # Przygotuj odpowiednie instrukcje w zależności od trybu
        if mode == "translate":
            language_names = {
                "en": "English",
                "pl": "Polish",
                "ru": "Russian",
                "fr": "French",
                "de": "German",
                "es": "Spanish",
                "it": "Italian",
                "zh": "Chinese"
            }
            target_lang_name = language_names.get(target_language, target_language)
            
            # Uniwersalne instrukcje niezależne od języka
            system_instruction = f"You are a professional translator. Your task is to translate text from the document to {target_lang_name}. Preserve the original text format."
            user_instruction = f"Translate the text from file {file_name} to {target_lang_name}. Preserve the structure and formatting of the original."
        else:  # tryb analyze
            system_instruction = "You are a helpful assistant who analyzes documents and files."
            user_instruction = f"Analyze file {file_name} and describe its contents. Provide key information and conclusions."
        
        messages = [
            {
                "role": "system", 
                "content": system_instruction
            },
            {
                "role": "user",
                "content": user_instruction
            }
        ]
        
        # Dla plików tekstowych możemy dodać zawartość bezpośrednio
        if file_extension in ['.txt', '.csv', '.md', '.json', '.xml', '.html', '.js', '.py', '.cpp', '.c', '.java']:
            try:
                # Próbuj odkodować jako UTF-8
                file_text = file_content.decode('utf-8')
                messages[1]["content"] += f"\\n\\nFile content:\\n\\n{file_text}"
            except UnicodeDecodeError:
                # Jeśli nie możemy odkodować, traktuj jako plik binarny
                messages[1]["content"] += "\\n\\nThe file contains binary data that cannot be displayed as text."
        
        response = await client.chat.completions.create(
            model="gpt-4o",  # Używamy GPT-4o dla lepszej jakości
            messages=messages,
            max_tokens=1500  # Zwiększamy limit tokenów dla dłuższych tekstów
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Błąd analizy dokumentu: {e}")
        return f"Sorry, an error occurred while analyzing the document: {str(e)}"
'''
    
    # Zamieniamy stare funkcje na nowe
    content = re.sub(r"async def analyze_image.*?return f\"Przepraszam, wystąpił błąd podczas analizy obrazu: {str\(e\)}\"\s*", analyze_image_modified, content, flags=re.DOTALL)
    content = re.sub(r"async def analyze_document\(file_content, file_name, mode=\"analyze\", target_language=\"en\"\):.*?return f\"Przepraszam, wystąpił błąd podczas analizy dokumentu: {str\(e\)}\"\s*", analyze_document_modified, content, flags=re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)
    
    print("Plik utils/openai_client.py naprawiony.")

def fix_translate_handler():
    """Naprawia funkcję tłumaczenia w translate_handler.py"""
    print("Naprawianie pliku handlers/translate_handler.py...")
    
    file_path = "handlers/translate_handler.py"
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Poprawiamy funkcję translate_text
    translate_text_modified = '''
async def translate_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text, target_lang="en"):
    """Tłumaczy podany tekst na określony język"""
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy użytkownik ma wystarczającą liczbę kredytów
    credit_cost = 3  # Koszt tłumaczenia tekstu
    if not check_user_credits(user_id, credit_cost):
        await update.message.reply_text(get_text("subscription_expired", language))
        return
    
    # Wyślij informację o rozpoczęciu tłumaczenia
    message = await update.message.reply_text(
        get_text("translating_text", language, default="Translating text, please wait...")
    )
    
    # Wyślij informację o aktywności bota
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    # Wykonaj tłumaczenie korzystając z API OpenAI
    from utils.openai_client import chat_completion
    
    # Uniwersalny prompt niezależny od języka
    system_prompt = f"You are a professional translator. Translate the following text to {target_lang}. Preserve formatting. Only return the translation."
    
    # Przygotuj wiadomości dla API
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text}
    ]
    
    # Wykonaj tłumaczenie
    translation = await chat_completion(messages, model="gpt-3.5-turbo")
    
    # Odejmij kredyty
    deduct_user_credits(user_id, credit_cost, f"Translation to {target_lang}")
    
    # Wyślij tłumaczenie
    source_lang_name = get_language_name(language)
    target_lang_name = get_language_name(target_lang)
    
    await message.edit_text(
        f"*{get_text('translation_result', language, default='Translation result')}* ({source_lang_name} → {target_lang_name})\\n\\n{translation}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Sprawdź aktualny stan kredytów
    credits = get_user_credits(user_id)
    if credits < 5:
        await update.message.reply_text(
            f"{get_text('low_credits_warning', language)} {get_text('low_credits_message', language, credits=credits)}",
            parse_mode=ParseMode.MARKDOWN
        )
'''
    
    # Zamieniamy starą funkcję na nową
    content = re.sub(r"async def translate_text.*?parse_mode=ParseMode\.MARKDOWN\s*\)", translate_text_modified, content, flags=re.DOTALL)
    
    # Poprawiamy funkcję obsługi komendy translate
    translate_command_modified = '''
async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługa komendy /translate
    Instruuje użytkownika jak korzystać z funkcji tłumaczenia
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy komenda zawiera argumenty (tekst do tłumaczenia i docelowy język)
    if context.args and len(context.args) >= 2:
        # Format: /translate [język_docelowy] [tekst]
        # np. /translate en Witaj świecie!
        target_lang = context.args[0].lower()
        text_to_translate = ' '.join(context.args[1:])
        await translate_text(update, context, text_to_translate, target_lang)
        return
    
    # Sprawdź, czy wiadomość jest odpowiedzią na zdjęcie lub dokument
    if update.message.reply_to_message:
        # Obsługa odpowiedzi na wcześniejszą wiadomość
        replied_message = update.message.reply_to_message
        
        # Ustal docelowy język tłumaczenia z argumentów komendy
        target_lang = "en"  # Domyślnie angielski
        if context.args and len(context.args) > 0:
            target_lang = context.args[0].lower()
        
        if replied_message.photo:
            # Odpowiedź na zdjęcie - wykonaj tłumaczenie tekstu ze zdjęcia
            await translate_photo(update, context, replied_message.photo[-1], target_lang)
            return
        elif replied_message.document:
            # Odpowiedź na dokument - wykonaj tłumaczenie dokumentu
            await translate_document(update, context, replied_message.document, target_lang)
            return
        elif replied_message.text:
            # Odpowiedź na zwykłą wiadomość tekstową
            await translate_text(update, context, replied_message.text, target_lang)
            return
    
    # Jeśli nie ma odpowiedzi ani argumentów, wyświetl instrukcje
    instruction_text = get_text("translate_instruction", language, default="📄 **Text Translation**\\n\\nAvailable options:\\n\\n1️⃣ Send a photo with text to translate and add /translate in the caption or reply to the photo with the /translate command\\n\\n2️⃣ Send a document and reply to it with the /translate command\\n\\n3️⃣ Use the command /translate [target_language] [text]\\nFor example: /translate en Hello world!\\n\\nAvailable target languages: en (English), pl (Polish), ru (Russian), fr (French), de (German), es (Spanish), it (Italian), zh (Chinese)")
    
    await update.message.reply_text(
        instruction_text,
        parse_mode=ParseMode.MARKDOWN
    )
'''
    
    # Zamieniamy starą funkcję na nową
    content = re.sub(r"async def translate_command.*?parse_mode=ParseMode\.MARKDOWN\s*\)", translate_command_modified, content, flags=re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)
    
    print("Plik handlers/translate_handler.py naprawiony.")

def fix_help_handler():
    """Naprawia teksty pomocy w translations.py"""
    print("Naprawianie pliku translations.py...")
    
    file_path = "utils/translations.py"
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Poprawiamy tekst pomocy - zamieniamy /start na /help
    content = content.replace('/start - Pokaż to menu', '/help - Pokaż to menu')
    content = content.replace('/start - Show this menu', '/help - Show this menu')
    content = content.replace('/start - Показать это меню', '/help - Показать это меню')
    
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)
    
    print("Plik translations.py naprawiony.")

def fix_get_user_language():
    """Naprawia funkcję get_user_language w menu_handler.py"""
    print("Naprawianie funkcji get_user_language...")
    
    # Naprawiamy we wszystkich plikach, które zawierają tę funkcję
    files_to_check = [
        "handlers/menu_handler.py",
        "handlers/start_handler.py",
        "handlers/code_handler.py",
        "handlers/credit_handler.py"
    ]
    
    for file_path in files_to_check:
        if not os.path.exists(file_path):
            print(f"Plik {file_path} nie istnieje, pomijam.")
            continue
            
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        if "def get_user_language" in content:
            # Wydzielamy funkcję get_user_language
            pattern = r"def get_user_language.*?return \"pl\"\s*"
            match = re.search(pattern, content, re.DOTALL)
            
            if match:
                old_func = match.group(0)
                
                # Tworzę nową funkcję z poprawką - zmieniamy domyślny język na ten z language_code w bazie
                new_func = old_func.replace(
                    '# Domyślny język, jeśli nie znaleziono w bazie\n    return "pl"',
                    '''# Sprawdź language_code, jeśli nie znaleziono language
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
        return "pl"'''
                )
                
                content = content.replace(old_func, new_func)
                
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(content)
                
                print(f"Naprawiono funkcję get_user_language w pliku {file_path}")
            else:
                print(f"Nie udało się znaleźć pełnej funkcji get_user_language w pliku {file_path}")
        else:
            print(f"Plik {file_path} nie zawiera funkcji get_user_language, pomijam.")

def fix_mode_handler():
    """Poprawia handler trybów w main.py"""
    print("Naprawianie handlera trybów w main.py...")
    
    file_path = "main.py"
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Poprawmy obsługę callbacków dla trybów
    pattern = r'if query\.data\.startswith\("mode_"\):(.*?)return'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        old_code = match.group(1)
        new_code = '''
        print(f"Rozpoznano callback trybu: {query.data}")
        mode_id = query.data[5:]  # Pobierz ID trybu (usuń prefix "mode_")
        try:
            from handlers.mode_handler import handle_mode_selection
            await handle_mode_selection(update, context, mode_id)
            return
        except Exception as e:
            print(f"Błąd w obsłudze trybu: {str(e)}")
            import traceback
            traceback.print_exc()
            # Wyślij informację o błędzie
            await query.answer(f"Error: {str(e)}")
            return
        '''
        
        content = content.replace(old_code, new_code)
        
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        
        print("Naprawiono handler trybów w main.py")
    else:
        print("Nie znaleziono fragmentu kodu do naprawy w main.py")

if __name__ == "__main__":
    print("Rozpoczynam naprawianie problemów z tłumaczeniami w bocie...")
    
    try:
        fix_openai_client()
        fix_translate_handler()
        fix_help_handler()
        fix_get_user_language()
        fix_mode_handler()
        
        print("\nWszystkie poprawki zostały pomyślnie zastosowane!")
        print("Zrestartuj bota, aby zmiany zostały zastosowane.")
    except Exception as e:
        print(f"Wystąpił błąd podczas naprawiania: {e}")