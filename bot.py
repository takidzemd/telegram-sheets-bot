import os
import json
import logging
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# ============================================================
#  НАСТРОЙКИ
# ============================================================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
PORT = int(os.environ.get('PORT', 10000))
RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL')

SPREADSHEET_ID = '1R1nU8B04MnX-RLtDwSMh97bM_zivjqW_zsYKEn8Pr-4'

SHEETS_CONFIG = {
    'graphics': {'display': '📊 График', 'sheet_name': 'Зоны', 'range': 'A1:AF10'},
    'metrics': {'display': '🚚 Тачка', 'sheet_name': 'Разгрузка+дежурство', 'range': 'A1:AF11'},
    'birthdays': {'display': '🏆 Конкурс', 'sheet_name': 'КОНКУРС 2.0', 'range': 'A1:Z8'},
    'tasks': {'display': '📋 Шпаргалка', 'sheet_name': 'Шпаргалка', 'range': 'A1:E69'}
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
#  ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS (Читаем JSON напрямую из переменной)
# ============================================================
def get_sheet_client():
    try:
        # Читаем JSON-строку напрямую из переменной окружения
        creds_json_str = os.environ.get('GOOGLE_CREDS_JSON')
        if not creds_json_str:
            logger.error("❌ Переменная GOOGLE_CREDS_JSON не найдена!")
            return None

        # Конвертируем строку в словарь (переносы \n превращаются в реальные переносы)
        creds_dict = json.loads(creds_json_str)

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        logger.error(f"Ошибка подключения: {e}")
        return None

def get_sheet_data(sheet_name, range_cells):
    try:
        client = get_sheet_client()
        if not client:
            return None
        sheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = sheet.worksheet(sheet_name)
        data = worksheet.get(range_cells)
        return data
    except Exception as e:
        logger.error(f"Ошибка чтения {sheet_name}: {e}")
        return f"ERROR: {str(e)}"

# ============================================================
#  СОЗДАНИЕ СКРИНШОТА
# ============================================================
def create_screenshot(data, sheet_name, range_cells):
    if not data:
        return None
    cell_width = 180
    cell_height = 35
    header_height = 50
    padding = 20
    rows = len(data)
    cols = max([len(row) for row in data]) if data else 0
    if rows == 0 or cols == 0:
        return None
    img_width = cols * cell_width + padding * 2
    img_height = rows * cell_height + header_height + padding * 2
    img = Image.new('RGB', (img_width, img_height), color='white')
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
        font_bold = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
        font_bold = font
    title = f"{sheet_name} (диапазон: {range_cells})"
    draw.text((padding, 10), title, fill='black', font=font_bold)
    y_offset = header_height
    for i, row in enumerate(data):
        x_offset = padding
        for j, cell in enumerate(row):
            draw.rectangle([(x_offset, y_offset), (x_offset + cell_width - 1, y_offset + cell_height - 1)], outline='gray', fill='white')
            text = str(cell)[:15]
            draw.text((x_offset + 5, y_offset + 8), text, fill='black', font=font)
            x_offset += cell_width
        y_offset += cell_height
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

# ============================================================
#  ОБРАБОТЧИКИ
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for key, config in SHEETS_CONFIG.items():
        keyboard.append([InlineKeyboardButton(config['display'], callback_data=key)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📋 **Выбери лист для просмотра:**", reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data
    config = SHEETS_CONFIG.get(key)
    if not config:
        await query.edit_message_text("❌ Лист не найден")
        return
    sheet_name = config['sheet_name']
    range_cells = config['range']
    display_name = config['display']
    await query.edit_message_text(f"📸 Делаю скриншот {display_name}...")
    data = get_sheet_data(sheet_name, range_cells)
    if isinstance(data, str):
        await query.message.reply_text(f"❌ Ошибка: {data}")
        return
    if not data:
        await query.message.reply_text(f"❌ Не удалось получить данные из {display_name}")
        return
    screenshot = create_screenshot(data, sheet_name, range_cells)
    if screenshot:
        await query.message.reply_photo(screenshot, caption=f"✅ **{display_name}**\nДиапазон: `{range_cells}`", parse_mode='Markdown')
    else:
        await query.message.reply_text(f"❌ Не удалось создать скриншот для {display_name}")
    await show_main_menu(query.message)

async def show_main_menu(message):
    keyboard = []
    for key, config in SHEETS_CONFIG.items():
        keyboard.append([InlineKeyboardButton(config['display'], callback_data=key)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text("📋 **Что ещё посмотрим?**", reply_markup=reply_markup, parse_mode='Markdown')

# ============================================================
#  ЗАПУСК ЧЕРЕЗ WEBHOOK
# ============================================================
def main():
    if not TELEGRAM_TOKEN:
        logger.error("❌ Токен не найден!")
        return
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    logger.info("🚀 Бот запущен!")
    if not RENDER_URL:
        logger.error("❌ Переменная RENDER_EXTERNAL_URL не найдена!")
        return
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TELEGRAM_TOKEN,
        webhook_url=f"{RENDER_URL}/{TELEGRAM_TOKEN}"
    )

if __name__ == "__main__":
    main()
