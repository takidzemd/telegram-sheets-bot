import os
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# ==================== НАСТРОЙКИ ====================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
SPREADSHEET_ID = '1R1nU8B04MnX-RLtDwSMh97bM_zivjqW_zsYKEn8Pr-4'

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
        logger.error(f"Ошибка подключения к Google Sheets: {e}")
        return None

def get_sheet_data(sheet_name, range_cells=None):
    try:
        client = get_sheet_client()
        if not client:
            return None
        sheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = sheet.worksheet(sheet_name)
        if range_cells:
            data = worksheet.get(range_cells)
        else:
            data = worksheet.get_all_values()
        return data
    except Exception as e:
        logger.error(f"Ошибка чтения данных из {sheet_name}: {e}")
        return None

# ==================== СОЗДАНИЕ СКРИНШОТА ====================
def create_screenshot(data, sheet_name):
    """Создает скриншот (PNG) из данных таблицы."""
    if not data or len(data) == 0:
        return None
    
    # Настройки
    font_size = 12
    header_font_size = 14
    cell_padding = 8
    cell_height = 30
    min_cell_width = 80
    
    # Определяем ширину столбцов
    col_widths = []
    for col_idx in range(len(data[0])):
        max_width = min_cell_width
        for row in data:
            if col_idx < len(row):
                text = str(row[col_idx])
                text_width = len(text) * 7
                max_width = max(max_width, text_width + cell_padding * 2)
        col_widths.append(max_width)
    
    # Размеры изображения
    padding = 15
    header_height = 40
    total_width = sum(col_widths) + padding * 2
    total_height = len(data) * cell_height + header_height + padding * 2
    
    # Создаем изображение
    img = Image.new('RGB', (total_width, total_height), color='#ffffff')
    draw = ImageDraw.Draw(img)
    
    # Загружаем шрифт
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", header_font_size)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
            font_bold = ImageFont.truetype("arialbd.ttf", header_font_size)
        except:
            font = ImageFont.load_default()
            font_bold = font
    
    # Заголовок
    draw.text((padding, 5), f"📊 {sheet_name}", fill='#2c3e50', font=font_bold)
    
    # Рисуем таблицу
    y_offset = header_height
    
    for row_idx, row in enumerate(data):
        x_offset = padding
        
        # Цвет строки
        if row_idx == 0:
            bg_color = '#2980b9'
            text_color = '#ffffff'
        elif row_idx % 2 == 0:
            bg_color = '#ecf0f1'
            text_color = '#2c3e50'
        else:
            bg_color = '#ffffff'
            text_color = '#2c3e50'
        
        for col_idx, cell in enumerate(row):
            cell_width = col_widths[col_idx]
            
            # Рисуем ячейку
            draw.rectangle(
                [(x_offset, y_offset), (x_offset + cell_width, y_offset + cell_height)],
                fill=bg_color,
                outline='#bdc3c7'
            )
            
            # Текст
            text = str(cell)
            text_x = x_offset + cell_padding
            text_y = y_offset + (cell_height - font_size) // 2
            
            if row_idx == 0:
                draw.text((text_x, text_y), text, fill=text_color, font=font_bold)
            else:
                draw.text((text_x, text_y), text, fill=text_color, font=font)
            
            x_offset += cell_width
        y_offset += cell_height
    
    # Сохраняем в память
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes

# ==================== НАСТРОЙКА ЛИСТОВ ====================
SHEETS_CONFIG = {
    'graphics': {
        'name': '📊 Графики',
        'range': 'A1:D20'
    },
    'metrics': {
        'name': '📈 Показатели',
        'range': 'A1:E15'
    },
    'birthdays': {
        'name': '🎂 Дни рождения',
        'range': 'A1:C50'
    },
    'tasks': {
        'name': '📋 Задачи',
        'range': 'A1:F30'
    }
}

# ==================== ОБРАБОТЧИКИ БОТА ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for key, config in SHEETS_CONFIG.items():
        keyboard.append([InlineKeyboardButton(config['name'], callback_data=f'sheet_{key}')])
    keyboard.append([InlineKeyboardButton("📋 Все данные", callback_data='sheet_all')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📋 **Выбери лист для просмотра:**\n\n"
        "Бот сделает скриншот данных из таблицы.\n"
        "✅ Данные всегда свежие — можно редактировать таблицу!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    
    if action == 'sheet_all':
        await query.edit_message_text("📸 Делаю скриншоты всех листов...")
        
        for key, config in SHEETS_CONFIG.items():
            clean_name = config['name'].replace('📊 ', '').replace('📈 ', '').replace('🎂 ', '').replace('📋 ', '')
            data = get_sheet_data(clean_name, config['range'])
            
            if data:
                screenshot = create_screenshot(data, config['name'])
                if screenshot:
                    await query.message.reply_photo(screenshot, caption=f"✅ {config['name']}")
                else:
                    await query.message.reply_text(f"⚠️ Не удалось создать скриншот для {config['name']}")
            else:
                await query.message.reply_text(f"❌ Нет данных для {config['name']}")
        
        await show_main_menu(query.message)
        return
    
    sheet_key = action.replace('sheet_', '')
    config = SHEETS_CONFIG.get(sheet_key)
    if not config:
        await query.edit_message_text("❌ Лист не найден")
        return
    
    sheet_name = config['name']
    clean_name = sheet_name.replace('📊 ', '').replace('📈 ', '').replace('🎂 ', '').replace('📋 ', '')
    
    await query.edit_message_text(f"📸 Делаю скриншот {sheet_name}...")
    
    data = get_sheet_data(clean_name, config['range'])
    
    if not data:
        await query.message.reply_text(f"❌ Не удалось получить данные из {sheet_name}")
        return
    
    screenshot = create_screenshot(data, sheet_name)
    
    if screenshot:
        await query.message.reply_photo(
            screenshot,
            caption=f"✅ **{sheet_name}**\nДиапазон: `{config['range']}`",
            parse_mode='Markdown'
        )
    else:
        await query.message.reply_text(f"⚠️ Не удалось создать скриншот для {sheet_name}")
    
    await show_main_menu(query.message)

async def show_main_menu(message):
    keyboard = []
    for key, config in SHEETS_CONFIG.items():
        keyboard.append([InlineKeyboardButton(config['name'], callback_data=f'sheet_{key}')])
    keyboard.append([InlineKeyboardButton("📋 Все данные", callback_data='sheet_all')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(
        "📋 **Что ещё посмотрим?**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ==================== ЗАПУСК ====================
def main():
    if not TELEGRAM_TOKEN:
        logger.error("❌ Токен не найден! Добавь TELEGRAM_TOKEN в Environment Variables на Render")
        return
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("🚀 Бот запущен и готов делать скриншоты!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()