from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from sd import generate_image
from consts import stable_diffusion_image_path, bot_token, negative_prompt, allowed_users, tg_channel_id
from images_db.db import add_images_to_db, get_images_and_last_id, init_db, get_image_by_pin_id
import images_db.db_approved
from pinterest_parser import like_pins
from telegram import InputMediaPhoto

password_file = 'passwords.txt'
print(bot_token)
bot = Bot(token=bot_token)
dp = Dispatcher()

async def validate_user(message: types.Message):
    if message.from_user.id not in allowed_users:
        await message.answer(
            "Ошибка: нет доступа"
        )
        return False
    return True

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await validate_user(message)
    await message.answer('''Привет. Команды:
1. /generate + текст промпта для нейронки
2. /parse_pinterest
3. /view_images
4. /view_approved_images
5. /post_approved
''')

@dp.message(Command("generate"))
async def cmd_generate(message: types.Message,
        command: CommandObject):
    await validate_user(message)
    if command.args is None:
        await message.answer(
            "Ошибка: не переданы аргументы"
        )
        return

    prompt = command.args
    await message.reply(f"Запуск генерации! Твой запрос: {prompt}." )

    response = await generate_image(prompt, negative_prompt)

    if response == 0:
        await bot.send_photo(message.chat.id, photo=types.FSInputFile(stable_diffusion_image_path))
    else:
        await message.reply(f"Возникла ошибка: {response}" )

@dp.message(Command("parse_pinterest"))
async def pinterest_images(message: types.Message,
        command: CommandObject):
    await validate_user(message)

    res = await add_images_to_db()

    if res == -1:
        message.reply(f"Возникла ошибка" )
    else:
        message.reply(f"Готово" )

async def send_images_with_checkboxes(chat_id):
    media_data, remaining_photos = get_images_and_last_id(1)
    if(len(media_data) == 0):
        await bot.send_message(chat_id, "Больше нет непросмотренных фото" )
        return
    
    id, pin_id, url = media_data[0]
    
    kb = [
        [types.InlineKeyboardButton(text="❤️", callback_data=f"like_{pin_id}")],
        [types.InlineKeyboardButton(text="👎", callback_data=f"dislike_{pin_id}")],
        [types.InlineKeyboardButton(text="Не хочу больше смотреть", callback_data=f"skip_{pin_id}")],
        ]
        
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb,)

    await bot.send_photo(
        chat_id=chat_id,
        photo=url,
        caption=f"Осталось еще {remaining_photos} не просмотренных фото.",
        reply_markup=keyboard
    )

@dp.message(Command("view_images"))
async def view_image(message: types.Message,
        command: CommandObject):
    if not await validate_user(message):
        return
    await send_images_with_checkboxes(message.chat.id)

@dp.message(Command("view_approved_images"))
async def approved_images(message: types.Message,
        command: CommandObject):

    if not await validate_user(message):
        return

    count = 10
    if command.args is not None and int(command.args) <= 20:
        count = int(command.args)
        
    media_data, remaining = images_db.db_approved.get_images(count)

    if len(media_data) < 1:
        await bot.send_message(message.chat.id, "Нет апрувнутых фото")

    count = len(media_data)

    media_files = [types.InputMediaPhoto(media=url) for id, pin_id, url in media_data]
    chunk_size = 10

    await bot.send_message(message.chat.id, "Следующие в предложке {count} фото из оставшихся {remaining}:")
    for i in range(0, len(media_files), chunk_size):
        chunk = media_files[i:i + chunk_size]
        await bot.send_media_group(chat_id=message.chat.id, media=chunk)

@dp.message(Command("post_approved"))
async def approved_images(message: types.Message,
        command: CommandObject):
    if not await validate_user(message):
        return

    media_data, remaining_photos = images_db.db_approved.get_images_and_last_id(5)

    if len(media_data) < 1:
        await bot.send_message(message.chat.id, "Нет апрувнутых фото")

    media_files = [types.InputMediaPhoto(media=url) for id, pin_id, url in media_data]
    chunk_size = 10

    for i in range(0, len(media_files), chunk_size):
        chunk = media_files[i:i + chunk_size]
        
        await bot.send_media_group(chat_id=tg_channel_id, media=chunk)

liked = []

@dp.callback_query(lambda c: c.data)
async def handle_reaction(callback_query: types.CallbackQuery):
    action, id = callback_query.data.split("_", 1)
    url, = await get_image_by_pin_id(id)

    if action == "like":
        liked.append((id, url))
        await send_images_with_checkboxes(callback_query.from_user.id)
    elif action == "dislike":
        await send_images_with_checkboxes(callback_query.from_user.id)
    elif action == "skip":
        pins_data = await like_pins(liked)

        pins_data = [{'pin_id': id, 'url': url} for id, url in liked]
        liked.clear()

        await images_db.db_approved.add_images_to_db(pins_data)

async def init_bot():
    init_db()
    await dp.start_polling(bot)
