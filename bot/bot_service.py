import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BotCommand, FSInputFile, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

from config import Config, BASE_DIR
import os

from app.services.core.cache_manager import get_schedule_data

log = logging.getLogger(__name__)

bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Словарь для хранения ID актуальных меню {user_id: message_id}
active_menu_messages = {}


# --- ХЕЛПЕРЫ ---

def get_delete_keyboard() -> types.InlineKeyboardMarkup:
    """Возвращает клавиатуру с одной кнопкой 'Удалить это сообщение'."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Удалить", callback_data="delete_message")
    return builder.as_markup()


def get_user_role(user_id: int) -> str:
    """Определяет роль пользователя по его Telegram ID."""
    user_id_str = str(user_id)
    if user_id_str in Config.TELEGRAM_ADMIN_IDS:
        return "admin"
    return "unknown"


async def _perform_update(schedule_name: str) -> str:
    """Выполняет обновление кэша и возвращает отформатированную строку с результатом."""
    log.info(f"Выполняется обновление для '{schedule_name}'...")
    result = get_schedule_data(schedule_name, force_update=True)
    if result.get("error"):
        icon = "❌"
        msg = f"<b>{schedule_name}</b>: Ошибка\n<code>{result['error']}</code>"
    else:
        icon = "✅"
        msg = f"<b>{schedule_name}</b>: Кэш успешно обновлен."
    return f"{icon} {msg}"


# --- ОБРАБОТЧИКИ КОМАНД И ОСНОВНЫХ КНОПОК ---

@dp.message(CommandStart())
async def command_start_handler(message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    role = get_user_role(user_id)

    if role == "admin":
        builder = InlineKeyboardBuilder()
        builder.button(text="⚙️ Открыть панель управления", callback_data="open_menu")
        await message.answer(
            f"👋 Привет, администратор {user_name}!",
            reply_markup=builder.as_markup()
        )
    else:
        await message.answer("ℹ️ Этот бот предназначен только для административных задач.")
        logging.warning(f"Неавторизованный доступ от пользователя {user_id} ({message.from_user.full_name})")

    try:
        await message.delete()
    except TelegramBadRequest as e:
        log.warning(f"Не удалось удалить сообщение с командой /start: {e}")


@dp.message(Command("menu"), lambda msg: get_user_role(msg.from_user.id) == 'admin')
async def command_menu_handler(message: Message):
    user_id = message.from_user.id

    if user_id in active_menu_messages:
        try:
            await bot.delete_message(chat_id=user_id, message_id=active_menu_messages[user_id])
            log.info(f"Старое меню для пользователя {user_id} удалено.")
        except TelegramBadRequest as e:
            log.warning(f"Не удалось удалить старое меню для {user_id}: {e}")
        del active_menu_messages[user_id]

    builder = InlineKeyboardBuilder()
    for name in Config.SCHEDULES.keys():
        builder.button(text=f"🔄 Обновить '{name}'", callback_data=f"update:{name}")
    builder.button(text="💥 Обновить все", callback_data="update:__all__")
    builder.adjust(2)

    image_path = os.path.join(BASE_DIR, 'bot', 'menu_image.png')
    image = FSInputFile(image_path)

    sent_message = await message.answer_photo(
        photo=image,
        caption="Панель управления расписаниями",
        reply_markup=builder.as_markup()
    )
    active_menu_messages[user_id] = sent_message.message_id
    log.info(f"Новое меню для пользователя {user_id} отправлено (ID: {sent_message.message_id})")

    try:
        await message.delete()
    except TelegramBadRequest as e:
        log.warning(f"Не удалось удалить сообщение с командой /menu: {e}")


# --- ОБРАБОТЧИКИ НАЖАТИЙ НА КНОПКИ (CALLBACKS) ---

@dp.callback_query(lambda c: c.data == 'open_menu', lambda c: get_user_role(c.from_user.id) == 'admin')
async def process_open_menu_callback(callback: CallbackQuery):
    await callback.answer()
    await command_menu_handler(callback.message)


@dp.callback_query(lambda c: c.data and c.data.startswith('update:'),
                   lambda c: get_user_role(c.from_user.id) == 'admin')
async def process_update_callback(callback: CallbackQuery):
    schedule_to_update = callback.data.split(':')[1]
    user_id = callback.from_user.id

    if user_id in active_menu_messages:
        try:
            await bot.delete_message(chat_id=user_id, message_id=active_menu_messages[user_id])
            log.info(f"Меню для {user_id} удалено после выбора опции.")
        except TelegramBadRequest as e:
            log.warning(f"Не удалось удалить меню для {user_id} после выбора: {e}")
        del active_menu_messages[user_id]

    if schedule_to_update == "__all__":
        await callback.answer("🚀 Начинаю обновление всех расписаний...", show_alert=False)
        tasks = [_perform_update(name) for name in Config.SCHEDULES.keys()]
        results = await asyncio.gather(*tasks)
        final_message = "✨ <b>Результаты полного обновления:</b>\n\n" + "\n".join(results)
        await callback.message.answer(
            final_message,
            parse_mode="HTML",
            reply_markup=get_delete_keyboard()  # <--- Добавляем кнопку
        )
    else:
        await callback.answer(f"🚀 Обновляю '{schedule_to_update}'...", show_alert=False)
        result_message = await _perform_update(schedule_to_update)
        await callback.message.answer(
            result_message,
            parse_mode="HTML",
            reply_markup=get_delete_keyboard()  # <--- Добавляем кнопку
        )


@dp.callback_query(lambda c: c.data == 'delete_message', lambda c: get_user_role(c.from_user.id) == 'admin')
async def process_delete_message_callback(callback: CallbackQuery):
    """
    Удаляет сообщение, к которому прикреплена кнопка.
    """
    try:
        await callback.message.delete()
        await callback.answer()
    except TelegramBadRequest as e:
        await callback.answer("Сообщение уже удалено.", show_alert=True)
        log.warning(f"Не удалось удалить сообщение для {callback.from_user.id}: {e}")


# --- ФУНКЦИЯ ЗАПУСКА БОТА ---

async def set_main_menu(bot: Bot):
    """Устанавливает команды, которые будут видны в кнопке 'Меню'."""
    main_menu_commands = [
        BotCommand(command="/start", description="👋 Перезапустить бота"),
        BotCommand(command="/menu", description="⚙️ Панель управления")
    ]
    await bot.set_my_commands(main_menu_commands)


async def main() -> None:
    """Точка входа для запуска бота."""
    logging.info("Запуск Telegram-бота...")
    await set_main_menu(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)