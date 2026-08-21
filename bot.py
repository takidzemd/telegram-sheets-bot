import os
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

# ==================== НАСТРОЙКИ ====================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
SPREADSHEET_ID = '1bCJNcdA6jooYQ6ZtQn6W34RteDsfN8pM1gWAdBM7idk'  # ТВОЙ ID!

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS ====================
def get_sheet_client():
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        logger.error(f"Ошибка подключения: {e}")
        return None

def get_sheet_data(sheet_name):
    try:
        client = get_sheet_client()
        if not client:
            return None
        sheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = sheet.worksheet(sheet_name)
        data = worksheet.get_all_values()
        return data
    except Exception as e:
        logger.error(f"Ошибка чтения {sheet_name}: {e}")
        return None

def format_data(data):
    if not data:
        return "Нет данных"
    result = ""
    for row in data[:20]:
        result += " | ".join([str(cell) for cell in row]) + "\n"
    return result

# ==================== НАСТРОЙКА ЛИСТОВ ====================
SHEETS_CONFIG = {
    'graphics': {
        'name': '📊 График',
        'sheet_name': 'Зоны',  # ← Это имя листа в Google Таблице!
        'range': 'A1:AF10'
    },
    'metrics': {
        'name': '🚚 Тачка',
        'sheet_name': 'Разгрузка+дежурство',  # ← Это имя листа в Google Таблице!
        'range': 'A1:AF11'
    },
    'birthdays': {
        'name': '🏆 Конкурс',
        'sheet_name': 'КОНКУРС 2.0',  # ← Это имя листа в Google Таблице!
        'range': 'A1:Z8'
    },
    'tasks': {
        'name': '📋 Шпаргалка',
        'sheet_name': 'Шпаргалка',  # ← Это имя листа в Google Таблице!
        'range': 'A1:E69'
    }
}

# ==================== ОБРАБОТЧИКИ БОТА ====================
def start(update, context):
    keyboard = []
    for key, config in SHEETS_CONFIG.items():
        keyboard.append([InlineKeyboardButton(config['name'], callback_data=f'sheet_{key}')])
    keyboard.append([InlineKeyboardButton("📋 Все данные", callback_data='all')])
    
    update.message.reply_text(
        "📋 **Выбери лист:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def button_handler(update, context):
    query = update.callback_query
    query.answer()
    action = query.data
    
    if action == 'all':
        query.edit_message_text("📋 Загружаю все данные...")
        for key, config in SHEETS_CONFIG.items():
            # Используем sheet_name из конфига!
            data = get_sheet_data(config['sheet_name'])
            if data:
                text = f"📌 **{config['name']}**\n```\n{format_data(data)}\n```"
                query.message.reply_text(text, parse_mode='Markdown')
            else:
                query.message.reply_text(f"❌ Нет данных для {config['name']}")
        return
    
    sheet_key = action.replace('sheet_', '')
    config = SHEETS_CONFIG.get(sheet_key)
    if not config:
        query.edit_message_text("❌ Лист не найден")
        return
    
    query.edit_message_text(f"📸 Получаю данные из {config['name']}...")
    
    # Используем sheet_name из конфига!
    data = get_sheet_data(config['sheet_name'])
    
    if data:
        text = f"📌 **{config['name']}**\n```\n{format_data(data)}\n```"
        query.message.reply_text(text, parse_mode='Markdown')
    else:
        query.message.reply_text(f"❌ Нет данных для {config['name']}")

def main():
    if not TELEGRAM_TOKEN:
        logger.error("❌ Токен не найден! Добавь TELEGRAM_TOKEN в Environment Variables")
        return
    
    updater = Updater(TELEGRAM_TOKEN)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("🚀 Бот запущен!")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
