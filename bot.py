import aiohttp
import cv2
import numpy as np
from io import BytesIO
import os
import asyncio
import logging
import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiogram.types import InputMediaPhoto, KeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
# from neuro_img import generate
from sd import generate_image
from consts import (
    stable_diffusion_image_path, 
    bot_token, 
    negative_prompt, 
    allowed_users, 
    tg_channel_id,
    tg_extra_channel_id,
    feedback_chat_id,
    tg_hot_channel
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
from video_db.db import (
    add_video_to_db, 
    get_video_and_last_id, 
    get_video_by_pin_id
)
from parse_topfapgirls import scrape_all_pages
import images_db.hot_images

TIMEZONE = "Europe/Moscow"

password_file = 'passwords.txt'

bot = Bot(token=bot_token)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone=TIMEZONE)

# Вспомогательная функция отправки изображений с чекбоксами
async def send_media_with_checkboxes(chat_id, media_data, remaining_media, send_media_func, media_type, extra=False):
    if not media_data:
        await send_message(chat_id, f"Больше нет непросмотренных {media_type}")
        return
    
    id, pin_id, url = media_data[0]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❤️", callback_data=f"like_{pin_id}_{media_type}_{extra}")],
        [InlineKeyboardButton(text="👎", callback_data=f"dislike_{pin_id}_{media_type}_{extra}")],
        [InlineKeyboardButton(text="Не хочу больше смотреть", callback_data=f"skip_{pin_id}_{media_type}_{extra}")]
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
2. /parse_hot_images + name
2. /view_hot_images + name
2. /parse_pinterest
3. /parse_non_asian_pinterest
'''
# Команды
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await bot.send_message(feedback_chat_id, f"{message.from_user.id}")
    if not await validate_user(message.from_user.id):

        await message.answer("Ошибка: нет доступа")
        return 
    button1 = KeyboardButton(text='/parse_pinterest')
    button2 = KeyboardButton(text='/view_images')
    button3 = KeyboardButton(text='/parse_non_asian_pinterest')
    button4 = KeyboardButton(text='/view_non_asian_images')
    
    keyboard_markup = ReplyKeyboardMarkup(
        keyboard=[
            [button1, button2],
            [button3, button4]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    await message.answer(welcome_message, reply_markup=keyboard_markup)

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

@dp.message(Command("parse_asian_pinterest"))
async def cmd_pinterest_images(message: types.Message, command: CommandObject):
    if not await validate_user(message.from_user.id):
        await message.answer("Ошибка: нет доступа")
        return

    await parse_pinterest_images(False)

@dp.message(Command("parse_non_asian_pinterest"))
async def cmd_parse_non_asian_pinterest(message: types.Message, command: CommandObject):
    if not await validate_user(message.from_user.id):
        await message.answer("Ошибка: нет доступа")
        return
    await parse_pinterest_images(True)

@dp.message(Command("view_non_asian_images"))
async def cmd_view_non_asian_images(message: types.Message,
        command: CommandObject):
    if not await validate_user(message.from_user.id):
        await message.answer("Ошибка: нет доступа")
        return
    media_data, remaining_media = get_images_and_last_id(1, True)
    await send_media_with_checkboxes(message.chat.id, media_data, remaining_media, send_photo, 'image', True)

@dp.message(Command("view_asian_images"))
async def cmd_view_image(message: types.Message,
        command: CommandObject):
    if not await validate_user(message.from_user.id):
        await message.answer("Ошибка: нет доступа")
        return
    media_data, remaining_media = get_images_and_last_id(1)

    await send_media_with_checkboxes(message.chat.id, media_data, remaining_media, send_photo, 'image')

@dp.message(Command("parse_hot_images"))
async def cmd_parse_hot_images(message: types.Message,
        command: CommandObject):
    if not await validate_user(message.from_user.id):
        await message.answer("Ошибка: нет доступа")
        return
    if command.args is None:
        await message.answer("Ошибка: не переданы аргументы")
        return

    id, name = command.args.split(' ')
    await bot.send_message(message.chat.id, command.args)

    await scrape_all_pages(id, name, bot)
    await bot.send_message(message.chat.id, "Парсинг по идее закончен")

@dp.message(Command("post_hot_images"))
async def cmd_view_hot_images(message: types.Message,
        command: CommandObject):
    if not await validate_user(message.from_user.id):
        await message.answer("Ошибка: нет доступа")
        return

    await post_hot_images(tg_hot_channel)

@dp.message(Command("get_all_girls"))
async def cmd_view_hot_images(message: types.Message,
        command: CommandObject):
    if not await validate_user(message.from_user.id):
        await message.answer("Ошибка: нет доступа")
        return
    girls_list = images_db.hot_images.get_all_girls()
    girls = '\n'.join(' '.join(tup) for tup in girls_list)
    await bot.send_message(feedback_chat_id, girls)

@dp.message(Command("get_random_girl"))
async def cmd_view_hot_images(message: types.Message,
        command: CommandObject):
    if not await validate_user(message.from_user.id):
        await message.answer("Ошибка: нет доступа")
        return
    id, name = images_db.hot_images.get_random_girl()
    await bot.send_message(feedback_chat_id, f"{id}: {name}")

@dp.message(Command("get_girl_images"))
async def cmd_view_hot_images(message: types.Message,
        command: CommandObject):
    if not await validate_user(message.from_user.id):
        await message.answer("Ошибка: нет доступа")
        return
    
    if command.args is None:
        await message.answer("Ошибка: не переданы аргументы")
        return

    id, name = command.args.split(' ')

    images, name = images_db.hot_images.get_girl_content(id, name, 3)
    media_files = [types.InputMediaPhoto(media=url) for url in images]
    media_files[0] = types.InputMediaPhoto(media=images[0], caption=name)
    await bot.send_media_group(chat_id=feedback_chat_id, media=media_files)

async def remove_bottom_50_pixels_from_url(image_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            if response.status != 200:
                print(f"Ошибка загрузки изображения по URL: {image_url}")
                return None
            
            data = await response.read()
            image_array = np.asarray(bytearray(data), dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            if image is None:
                print("Ошибка обработки изображения.")
                return None

            height = image.shape[0]
            if height > 50:
                cropped_image = image[:height-50, :]
                _, buffer = cv2.imencode('.jpg', cropped_image)
                return BytesIO(buffer)
            else:
                print("Изображение слишком мало для обрезки.")
                return None

async def post_hot_images(channel_id, bot):
    await bot.send_message(channel_id, 'Начинаю запланированную выкладку изображений в hot')
    images, name = images_db.hot_images.get_random_girl_images(10)
    
    media_files = []
    for idx, url in enumerate(images):
        cropped_image = await remove_bottom_50_pixels_from_url(url)
        if cropped_image:
            # Используем изображение с подписью только для первого элемента
            if idx == 0:
                media_files.append(types.InputMediaPhoto(media=cropped_image, caption=name))
            else:
                media_files.append(types.InputMediaPhoto(media=cropped_image))
    
    if media_files:
        await bot.send_media_group(chat_id=channel_id, media=media_files)

@dp.message(Command("view_video"))
async def cmd_view_video(message: types.Message,
        command: CommandObject):
    if not await validate_user(message.from_user.id):
        await message.answer("Ошибка: нет доступа")
        return
    await send_media_with_checkboxes(message.chat.id, get_video_and_last_id, send_video, 'video')

@dp.message(Command("view_approved_asian_images"))
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

    await bot.send_message(message.chat.id, f"Следующие в предложке {count} фото из оставшихся {remaining}, чтобы запостить /post_asian_approved:")
    for i in range(0, len(media_files), chunk_size):
        chunk = media_files[i:i + chunk_size]
        await bot.send_media_group(chat_id=message.chat.id, media=chunk)

@dp.message(Command("view_approved_non_asian_images"))
async def cmd_view_approved_non_asian_images(message: types.Message,
        command: CommandObject):
    if not await validate_user(message.from_user.id):
        await message.answer("Ошибка: нет доступа")
        return

    count = 10
    if command.args is not None and int(command.args) <= 20:
        count = int(command.args)
        
    media_data, remaining = images_db.db_approved.get_images(count, True)

    if len(media_data) < 1:
        await bot.send_message(message.chat.id, "Нет апрувнутых фото")

    count = len(media_data)

    media_files = [types.InputMediaPhoto(media=url) for id, pin_id, url in media_data]
    chunk_size = 10

    await bot.send_message(message.chat.id, f"Следующие в предложке {count} фото из оставшихся {remaining}, чтобы запостить /post_non_asian_approved:")
    for i in range(0, len(media_files), chunk_size):
        chunk = media_files[i:i + chunk_size]
        await bot.send_media_group(chat_id=message.chat.id, media=chunk)

@dp.message(Command("post_asian_approved"))
async def cmd_post_approved(message: types.Message,
        command: CommandObject):
    if not await validate_user(message.from_user.id):
        await message.answer("Ошибка: нет доступа")
        return
    
    count = 5
    if command.args is not None and int(command.args) <= 20:
        count = int(command.args)
    
    await post_approved_images(count, message.chat.id)

@dp.message(Command("post_non_asian_approved"))
async def cmd_post_approved(message: types.Message,
        command: CommandObject):
    if not await validate_user(message.from_user.id):
        await message.answer("Ошибка: нет доступа")
        return
    
    count = 5
    if command.args is not None and int(command.args) <= 20:
        count = int(command.args)
    
    await post_approved_images(count, message.chat.id, True)

@dp.message(Command("parse_basketball_videos"))
async def cmd_parse_basketball_videos(message: types.Message,
        command: CommandObject):
    res = await add_video_to_db()

    if res == -1:
        await bot.send_message(feedback_chat_id, f"Возникла ошибка в парсинге" )
    else:
        await bot.send_message(feedback_chat_id, f"Готово, парсинг заебок" )

@dp.message(Command("parse_folder"))
async def cmd_parse_fapfolder(message: types.Message,
        command: CommandObject):
    res = await scrape_fapfolder()
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
    action, id, content_type, extra = callback_query.data.split("_", 3)
    extra = extra.lower() == "true"
    if content_type == 'image':
        await bot.send_message(feedback_chat_id,f"{action} {id} {content_type} {extra}")
        url, = await get_image_by_pin_id(id, extra)
        media_data, remaining_media = get_images_and_last_id(1, extra)
        if action == "like":
            liked.append((id, url))
            await send_media_with_checkboxes(callback_query.from_user.id, media_data, remaining_media , send_photo, 'image',extra)
        elif action == "dislike":
            await send_media_with_checkboxes(callback_query.from_user.id, media_data, remaining_media, send_photo, 'image', extra)
    elif content_type == 'video':
        url, = await get_video_by_pin_id(id)
        media_data, remaining_media = get_video_and_last_id(1)
        if action == "like":
            liked.append((id, url))
            await send_media_with_checkboxes(callback_query.from_user.id, media_data, remaining_media, send_video, 'video')
        elif action == "dislike":
            await send_media_with_checkboxes(callback_query.from_user.id, media_data, remaining_media, send_video, 'video')
    
    if action == "skip":
        pins_data = await like_pins(liked, extra)

        pins_data = [{'pin_id': id, 'url': url} for id, url in liked]
        liked.clear()
        if content_type == 'image':
            await images_db.db_approved.add_images_to_db(pins_data, extra)
        elif content_type == 'video':
            await video_db.db_approved.add_video_to_db(pins_data)
        options = "/view_approved_non_asian_images" if extra==True else "/view_approved_asian_images"
        await bot.send_message(callback_query.from_user.id, f"Сохранил понравившееся! Попробуй {options}")

async def post_approved_images(number, feedback_chat_id, extra=False):
    media_data, remaining_photos = images_db.db_approved.get_images_and_last_id(number, extra)

    if len(media_data) < number:
        await bot.send_message(feedback_chat_id, "Недостаточно апрувнутых фото")
        return -1

    media_files = [types.InputMediaPhoto(media=url) for id, pin_id, url in media_data]
    chunk_size = 10

    for i in range(0, len(media_files), chunk_size):
        chunk = media_files[i:i + chunk_size]
        
        channel = tg_extra_channel_id if extra==True else tg_channel_id
        await bot.send_media_group(chat_id=channel, media=chunk)
    channel = "BeautyBliss" if extra==True else "Asian girls"
    await bot.send_message(feedback_chat_id, f"Осталось еще {remaining_photos} в предложке {channel}")

async def parse_pinterest_images(extra=False):
    res = await add_images_to_db(extra)

    if res == -1:
        await bot.send_message(feedback_chat_id, f"Возникла ошибка в парсинге" )
    else:
        options = "/view_non_asian_images" if extra==True else "/view_asian_images"
        await bot.send_message(feedback_chat_id, f"Готово, парсинг заебок. Попробуй посмотреть {options}" )

async def parse_pinterest_non_asian_images():
    res = await add_images_to_db(True)
    if res == -1:
        await bot.send_message(feedback_chat_id, f"Возникла ошибка в парсинге" )
    else:
        await bot.send_message(feedback_chat_id, f"Готово, парсинг заебок" )

async def schedule_parse_pinterest_images(extra=False):
    count = get_images_number(extra)
    channel = "BeautyBliss" if extra==True else "Asian girls"
    feedback_text = f"Начинаю запланированный парсинг картинок для тгк {channel}. На данный момент {count} фотографий"
    await bot.send_message(feedback_chat_id, feedback_text)
    if count < 100:
        await parse_pinterest_images(extra)

async def schedule_send_image(extra=False):
    channel = "BeautyBliss" if extra==True else "Asian girls"
    feedback_text = f"Начинаю запланированную выкладку картинок в тгк {channel}"
    await bot.send_message(feedback_chat_id, feedback_text)
    res = await post_approved_images(5, feedback_chat_id, extra)

    command = "/view_non_asian_images" if extra==True else "/view_asian_images"
    if res == '-1':
        await bot.send_message(feedback_chat_id, f"Не могу выкладывать фото в {channel}, пока вы не посмотрите предложку. Может быть выполним {command}?")

async def init_bot():
    images_db.db_approved.init_db()
    init_db()

    for i in range(0,23,4):
        scheduler.add_job(schedule_parse_pinterest_images, "cron", hour=i, minute=55, args=[True]) 
        scheduler.add_job(schedule_parse_pinterest_images, "cron", hour=i, minute=50, args=[False]) 

    scheduler.add_job(schedule_send_image, "cron", hour=10, minute=0, args=[True]) 
    scheduler.add_job(schedule_send_image, "cron", hour=20, minute=0, args=[False]) 
    
    scheduler.add_job(schedule_send_image, "cron", hour=10, minute=30, args=[False]) 
    scheduler.add_job(schedule_send_image, "cron", hour=20, minute=30, args=[True]) 

    scheduler.add_job(post_hot_images,"cron", hour=20, minute=30, args=[tg_hot_channel])

    scheduler.start()
    await dp.start_polling(bot)