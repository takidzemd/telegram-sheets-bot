import os
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
#  ЗАШИТЫЙ КЛЮЧ (НЕ ТРОГАЙ ЭТОТ БЛОК!)
# ============================================================
CREDS_DICT = {
  "type": "service_account",
  "project_id": "telegrambotsheets-506205",
  "private_key_id": "f33e5b992f3bfc3c50ccc634c97e2cad6b104fb2",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCX4z92eoGDvJeW\nUNGkI2MiulbXjM+GcqjZkRoGjVzKXuUWYLYdpS6FeHPRqXk42337DT9YmgBXRrK1\npRumL+DBJnlByEPuJTEs+xA3V3RNCFupZ8Fo6Sqwq7KP2Kp5+WDKucoVpixGXKLV\nTMhpdgzDHBA4u9MNdAXxp+LwUWvGD5CsjEFz3ElIzBGjbe5iY7ZfMzEUatDn6jGq\nPAwF5L54Bw9Uslv/pbR12vYYau3foPjXdlp6Mlx2KSvHXgrtPXzdiIhuaEigpLBL\nnbt2f8qTtpb6aZPG8rVBAXPT4SeCCRJhnHDp9uzuagalR3KiIJHN0hFk0hihsx06\nEpZPmICfAgMBAAECggEAA5LlFOEB5HFdrIB/KfzOZsTmgfgbj/BCB/pZBCaHSCJU\nx/tIVlLFn/Qdo/3ak+pA+/Krz42yPao+ddgUHx9X94XzzZp7DwLGycioNeg4sHFS\n3UU3mDoTWbnXRz4J+q/lgI+iU62xn//l7MnAhyOmSmDQx4MdZzeYUA4hQx/uF0re\n9EM8wye+zhwhDLJnB4yjn1nvCm7Rjimc2dsGF2wziCN/WQaD67Qf68xwe59LaknF\nETeqC/pmp+bg6gq1xCgZ8WtrRnHVaW+NBaLwSQBBR3CmhWkzd2GVcqxLoLjEUdNk\nH04chMh4tCyXo5R6kRsFRKnOgiEKT58lyR3jWIQlbQKBgQDIIRuQtYVVZkd8g+Q+\nxJ1yA01B7gAS0JWhqfvtZ5YYKoB+YVNPRLoqzRlVw02TIWtu50Ci/3gD4ZE1Y36o\n+i9zJxRJioYnybe5TntbnMAAo8mkkipCHxNSGkUJZCJLEmYpH1h3ruigwifXUsmA\nYzIpQVKWHNHa0wK6GD0FEQ1LiwKBgQDCSmUPE5LljhdvCgI4I49nHW3kXLUuwQHP\nA9PprNlEIC+qoMIHtyBKUyeTdmlwrM+Q/VmxBqKkJ+s/v+Z9PhiTeAyggOU16Rj8\nFB74q41jlS2+Vr8/K3tCFaw7BHrLexuA4UzSGc9a2Oo/YlvTPqLFiynvy6K3GtUc\nYq23qrqRvQKBgDSQ7aqe4zzBNrmv8v3BqxFNaLeOihpnC0aBXZjIApaqY0HO0pEZ\nnkSrxqHOQMwKlSt2NnYZ4C40y21YiuZbgKcgdqWyavZ8d3OG98PiclQ4sTg25D6l\n5u9D0ypaUN+jH45hm10kZhoDpW9bYW4FoCFR9R1UyJJPpoG26CAykGltAoGAHbSK\nJvfzKa3D33JETJkDP9y8BII4IWHZCPGo4L1Qqp3RK+FQQ1ZgVXzJPD6KeHOzeJOD\ntxEwpLCFw0Vv1A4+a62bIJ8UbF2rOD9LTPHNuEACsmtI6juXqM7vekaBD8NOvTG1\nMRpJHba0eeRr7axR7qoMS2FzC1PK6YAc10v/InECgYBygHZlMoEdpw4u9Wf5UAwh\n48gbb98xfJCLvM0/WAotToQOyn4tUREn+UwYIQYAdveGnmR0H9L03CPZeoyHKlKF\nbADZlluk/uecsaO1RPher11T0t8nIDIncLTpKubYKcRntRZnOMjwIrLQP8ApZeW9\nIAhBu/vynIk2XyykM/mmuQ==\n-----END PRIVATE KEY-----\n",
  "client_email": "bot-access@telegrambotsheets-506205.iam.gserviceaccount.com",
  "client_id": "114408237095170372228",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/bot-access%40telegrambotsheets-506205.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

# ============================================================
#  ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS
# ============================================================
def get_sheet_client():
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
        # Используем зашитый словарь CREDS_DICT
        creds = Credentials.from_service_account_info(CREDS_DICT, scopes=scope)
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
