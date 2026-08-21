import os
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import io

# ==================== НАСТРОЙКИ ====================
TELEGRAM_TOKEN = 'ТВОЙ_ТОКЕН_ОТ_BOTFATHER'  # Заменить!
SPREADSHEET_ID = 'ID_ТВОЕЙ_ТАБЛИЦЫ'         # Заменить! ID из URL таблицы

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS ====================
def get_sheet_client():
    """Создает клиент для работы с Google Sheets."""
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
    """
    Получает данные из указанного листа.
    
    Args:
        sheet_name (str): Название листа
        range_cells (str): Диапазон ячеек (например, "A1:D10")
    
    Returns:
        list: Данные в виде списка списков
    """
    try:
        client = get_sheet_client()
        if not client:
            return None
        
        sheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = sheet.worksheet(sheet_name)
        
        if range_cells:
            # Получаем только указанный диапазон
            data = worksheet.get(range_cells)
        else:
            # Получаем все данные
            data = worksheet.get_all_values()
        
        return data
    except Exception as e:
        logger.error(f"Ошибка чтения данных из {sheet_name}: {e}")
        return None

def create_screenshot(data, sheet_name, title=""):
    """
    Создает скриншот из данных таблицы.
    
    Args:
        data (list): Данные из таблицы
        sheet_name (str): Название листа (для заголовка)
        title (str): Дополнительный заголовок
    
    Returns:
        BytesIO: Поток с изображением
    """
    if not data:
        return None
    
    # Настройки изображения
    cell_width = 200
    cell_height = 40
    header_height = 60
    padding = 20
    
    # Определяем размеры таблицы
    rows = len(data)
    cols = max([len(row) for row in data]) if data else 0
    
    # Вычисляем размеры изображения
    img_width = cols * cell_width + padding * 2
    img_height = rows * cell_height + header_height + padding * 2
    
    # Создаем изображение
    img = Image.new('RGB', (img_width, img_height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Пытаемся загрузить шрифт (если нет, используем стандартный)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
        font_bold = ImageFont.truetype("arialbd.ttf", 16)
    except:
        font = ImageFont.load_default()
        font_bold = font
    
    # Рисуем заголовок
    title_text = f"{sheet_name}: {title}" if title else sheet_name
    draw.text((padding, 10), title_text, fill='black', font=font_bold)
    
    # Рисуем таблицу
    y_offset = header_height
    
    for i, row in enumerate(data):
        x_offset = padding
        for j, cell in enumerate(row):
            # Рисуем ячейку
            draw.rectangle(
                [(x_offset, y_offset), (x_offset + cell_width - 1, y_offset + cell_height - 1)],
                outline='gray',
                fill='white'
            )
            # Пишем текст
            draw.text((x_offset + 5, y_offset + 10), str(cell), fill='black', font=font)
            x_offset += cell_width
        y_offset += cell_height
    
    # Сохраняем в поток
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes

# ==================== ОПРЕДЕЛЕНИЕ ЛИСТОВ И ДИАПАЗОНОВ ====================
# Здесь ты настраиваешь, какие листы и диапазоны показывать
SHEETS_CONFIG = {
    'graphics': {
        'name': '📊 Графики',
        'range': 'A1:D20'  # Диапазон ячеек для скриншота
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

# ==================== ОБРАБОТЧИКИ КОМАНД БОТА ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает главное меню с кнопками."""
    keyboard = []
    
    for key, config in SHEETS_CONFIG.items():
        keyboard.append([InlineKeyboardButton(config['name'], callback_data=f'sheet_{key}')])
    
    # Добавляем кнопку для всех данных
    keyboard.append([InlineKeyboardButton("📋 Все данные", callback_data='sheet_all')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📋 **Выбери лист для просмотра:**\n\n"
        "Я покажу актуальные данные из твоей Google Таблицы.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия на кнопки."""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    # Если пользователь нажал на кнопку "Все данные"
    if action == 'sheet_all':
        await query.edit_message_text("📋 Загружаю все данные...")
        
        for key, config in SHEETS_CONFIG.items():
            data = get_sheet_data(config['name'].replace('📊 ', '').replace('📈 ', '').replace('🎂 ', '').replace('📋 ', ''), config['range'])
            if data:
                screenshot = create_screenshot(data, config['name'])
                if screenshot:
                    await query.message.reply_photo(screenshot, caption=f"✅ {config['name']}")
                else:
                    await query.message.reply_text(f"⚠️ Не удалось создать скриншот для {config['name']}")
            else:
                await query.message.reply_text(f"❌ Нет данных для {config['name']}")
        
        # Возвращаем меню
        await show_main_menu(query.message)
        return
    
    # Обрабатываем выбор конкретного листа
    sheet_key = action.replace('sheet_', '')
    config = SHEETS_CONFIG.get(sheet_key)
    
    if not config:
        await query.edit_message_text("❌ Лист не найден")
        return
    
    sheet_name = config['name']
    range_cells = config['range']
    
    # Убираем эмодзи из названия для запроса
    clean_name = sheet_name.replace('📊 ', '').replace('📈 ', '').replace('🎂 ', '').replace('📋 ', '')
    
    await query.edit_message_text(f"📸 Получаю данные из {sheet_name}...")
    
    # Получаем данные
    data = get_sheet_data(clean_name, range_cells)
    
    if not data:
        await query.message.reply_text(f"❌ Не удалось получить данные из {sheet_name}")
        return
    
    # Создаем скриншот
    screenshot = create_screenshot(data, sheet_name, f"(диапазон: {range_cells})")
    
    if screenshot:
        await query.message.reply_photo(
            screenshot,
            caption=f"✅ **{sheet_name}**\nДиапазон: `{range_cells}`",
            parse_mode='Markdown'
        )
    else:
        await query.message.reply_text(f"⚠️ Не удалось создать скриншот для {sheet_name}")
    
    # Возвращаем меню
    await show_main_menu(query.message)

async def show_main_menu(message):
    """Показывает главное меню после отправки данных."""
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

# ==================== ЗАПУСК БОТА ====================
def main():
    """Запуск бота."""
    # Создаем приложение
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Запускаем бота
    logger.info("🚀 Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()