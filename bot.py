import os
import asyncio
import logging
import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiogram.types import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from sd import generate_image
from consts import (
    stable_diffusion_image_path, 
    bot_token, 
    negative_prompt, 
    allowed_users, 
    tg_channel_id
)
from images_db.db import (
    add_images_to_db, 
    get_images_and_last_id, 
    init_db, 
    get_image_by_pin_id, 
    get_images_number
)
import images_db.db_approved
import video_db.db_approved
from pinterest_parser import like_pins, parse_basketball_video
# from parse_dzen import parse_dzen
from video_db.db import (
    add_video_to_db, 
    get_video_and_last_id, 
    get_video_by_pin_id
)

TIMEZONE = "Europe/Moscow"

password_file = 'passwords.txt'
feedback_chat_id = '879672892'

bot = Bot(token=bot_token)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone=TIMEZONE)

# Вспомогательная функция отправки изображений с чекбоксами
async def send_media_with_checkboxes(chat_id, get_media_func, send_media_func, media_type):
    media_data, remaining_media = get_media_func(1)
    if not media_data:
        await send_message(chat_id, f"Больше нет непросмотренных {media_type}")
        return
    
    id, pin_id, url = media_data[0]
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❤️", callback_data=f"like_{pin_id}_{media_type}")],
        [InlineKeyboardButton(text="👎", callback_data=f"dislike_{pin_id}_{media_type}")],
        [InlineKeyboardButton(text="Не хочу больше смотреть", callback_data=f"skip_{pin_id}_{media_type}")]
    ])
    
    await send_media_func(
        chat_id,
        url,
        f"Осталось еще {remaining_media} не просмотренных {media_type}.",
        kb
    )

# Универсальная функция отправки фото или видео
async def send_photo(chat_id, url, caption="", reply_markup=None):
    await bot.send_photo(chat_id, photo=url, caption=caption, reply_markup=reply_markup)

async def send_video(chat_id, url, caption="", reply_markup=None):
    await bot.send_video(chat_id, video=url, caption=caption, reply_markup=reply_markup)

# Утилиты
async def send_message(chat_id, text):
    await bot.send_message(chat_id, text)

async def validate_user(user_id):
    if user_id not in allowed_users:
        return False
    return True

welcome_message = '''Привет. Команды:
1. /generate string - промпт
2. /parse_pinterest
3. /view_images - просмотреть фото и дополнить предложку
4. /view_approved_images number - количество до 20
5. /post_approved number - количество до 10
6. /view_video - пока не работает
7. /parse_basketball_videos - пока не работает
8. /parse_dzen - закоп
'''
# Команды
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not await validate_user(message.from_user.id):
        await message.answer("Ошибка: нет доступа")
        return 
    await message.answer(welcome_message)

@dp.message(Command("generate"))
async def cmd_generate(message: types.Message, command: CommandObject):
    if not await validate_user(message.from_user.id):
        await message.answer("Ошибка: нет доступа")
        return

    if command.args is None:
        await message.answer("Ошибка: не переданы аргументы")
        return

    prompt = command.args
    await message.reply(f"Запуск генерации! Твой запрос: {prompt}.")
    
    response = await generate_image(prompt, negative_prompt)
    
    if response == 0:
        await bot.send_photo(message.chat.id, photo=types.FSInputFile(stable_diffusion_image_path))
    else:
        await message.reply(f"Возникла ошибка: {response}")

@dp.message(Command("parse_pinterest"))
async def cmd_pinterest_images(message: types.Message, command: CommandObject):
    if not await validate_user(message.from_user.id):
        await message.answer("Ошибка: нет доступа")
        return

    await parse_pinterest_images()

@dp.message(Command("view_images"))
async def cmd_view_image(message: types.Message,
        command: CommandObject):
    if not await validate_user(message.from_user.id):
        await message.answer("Ошибка: нет доступа")
        return
    await send_media_with_checkboxes(message.chat.id, get_images_and_last_id, send_photo, 'image')

@dp.message(Command("view_video"))
async def cmd_view_video(message: types.Message,
        command: CommandObject):
    if not await validate_user(message.from_user.id):
        await message.answer("Ошибка: нет доступа")
        return
    await send_media_with_checkboxes(message.chat.id, get_video_and_last_id, send_video, 'video')

@dp.message(Command("view_approved_images"))
async def cmd_view_approved_images(message: types.Message,
        command: CommandObject):
    if not await validate_user(message.from_user.id):
        await message.answer("Ошибка: нет доступа")
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

    await bot.send_message(message.chat.id, f"Следующие в предложке {count} фото из оставшихся {remaining}:")
    for i in range(0, len(media_files), chunk_size):
        chunk = media_files[i:i + chunk_size]
        await bot.send_media_group(chat_id=message.chat.id, media=chunk)

@dp.message(Command("post_approved"))
async def cmd_post_approved(message: types.Message,
        command: CommandObject):
    if not await validate_user(message):
        return
    
    count = 5
    if command.args is not None and int(command.args) <= 20:
        count = int(command.args)
    
    await post_approved_images(count, message.chat.id)

@dp.message(Command("parse_basketball_videos"))
async def cmd_parse_basketball_videos(message: types.Message,
        command: CommandObject):
    res = await add_video_to_db()

    if res == -1:
        await bot.send_message(feedback_chat_id, f"Возникла ошибка в парсинге" )
    else:
        await bot.send_message(feedback_chat_id, f"Готово, парсинг заебок" )

# @dp.message(Command("parse_dzen"))
# async def dzen(message: types.Message,
#         command: CommandObject):

#     news = await parse_dzen('it')
#     if news == -1:
#         bot.send_message(message.chat.id, 'Ошибка, предположительно: нет такого канала')
    
#     for new in news:
#         text = f"*{new["title"]}*"

#         for txt in new["content"]:
#             text +="\n \n"+ txt

#         if new["image_url"]:
#             await bot.send_photo(message.chat.id, new["image_url"], caption=text, parse_mode='markdown')
#         else:
#             await bot.send_message(message.chat.id, text, parse_mode='markdown')

liked = []

@dp.callback_query(lambda c: c.data)
async def handle_reaction(callback_query: types.CallbackQuery):
    action, id, content_type = callback_query.data.split("_", 2)
    if content_type == 'image':
        url, = await get_image_by_pin_id(id)
        if action == "like":
            liked.append((id, url))
            await send_media_with_checkboxes(callback_query.from_user.id, get_images_and_last_id, send_photo, 'image')
        elif action == "dislike":
            await send_media_with_checkboxes(callback_query.from_user.id, get_images_and_last_id, send_photo, 'image')
    elif content_type == 'video':
        url, = await get_video_by_pin_id(id)
        if action == "like":
            liked.append((id, url))
            await send_media_with_checkboxes(callback_query.from_user.id, get_video_and_last_id, send_video, 'video')
        elif action == "dislike":
            await send_media_with_checkboxes(callback_query.from_user.id, get_video_and_last_id, send_video, 'video')
    
    if action == "skip":
        pins_data = await like_pins(liked)

        pins_data = [{'pin_id': id, 'url': url} for id, url in liked]
        liked.clear()
        if content_type == 'image':
            await images_db.db_approved.add_images_to_db(pins_data)
        elif content_type == 'video':
            await video_db.db_approved.add_video_to_db(pins_data)
        await bot.send_message(callback_query.from_user.id, f"Сохранил понравившееся!")

async def post_approved_images(number, feedback_chat_id):
    media_data, remaining_photos = images_db.db_approved.get_images_and_last_id(number)

    if len(media_data) < number:
        await bot.send_message(feedback_chat_id, "Недостаточно апрувнутых фото")
        return -1

    media_files = [types.InputMediaPhoto(media=url) for id, pin_id, url in media_data]
    chunk_size = 10

    for i in range(0, len(media_files), chunk_size):
        chunk = media_files[i:i + chunk_size]
        
        await bot.send_media_group(chat_id=tg_channel_id, media=chunk)

utro = "утром"
evening = "вечером"
async def send_image(morning):
    if morning:
        await bot.send_message(feedback_chat_id, f"Начинаю запланированную выкладку картинок {utro}")
    else:
        await bot.send_message(feedback_chat_id, f"Начинаю запланированную выкладку картинок {evening}")
    res = await post_approved_images(5, feedback_chat_id)

    if res == '-1':
        await bot.send_message(feedback_chat_id, "Не могу выкладывать фото, пока вы не посмотрите предложку. Может быть выполним /view_images?")
    else:
        if morning:
            scheduler.add_job(send_image, "cron", hour=19, minute=0, args=[False]) 
        else:
            scheduler.add_job(send_image, "cron", hour=10, minute=0, args=[True]) 

async def parse_pinterest_images():
    res = await add_images_to_db()

    if res == -1:
        await bot.send_message(feedback_chat_id, f"Возникла ошибка в парсинге" )
    else:
        await bot.send_message(feedback_chat_id, f"Готово, парсинг заебок" )

async def schedule_parse_pinterest_images():
    count = get_images_number()
    if count < 100:
        await parse_pinterest_images()

    now = datetime.datetime.now()
    scheduler.add_job(parse_pinterest_images, "cron", hour=now.hour+1, minute=now.minute) 

async def init_bot():
    init_db()
    scheduler.add_job(send_image, "cron", hour=10, minute=0, args=[True]) 
    scheduler.add_job(schedule_parse_pinterest_images, "cron", hour=23, minute=0) 

    scheduler.start()
    await dp.start_polling(bot)