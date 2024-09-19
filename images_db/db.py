import asyncio
import sqlite3
import os
from pathlib import Path
from playwright.async_api import async_playwright
from pinterest_parser import parse_pinterest_images, parse_pinterest_non_asian_images

# Убедитесь, что существует директория для сохранения изображений
IMAGES_DIR = 'images'
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

# Инициализация БД
DATABASE = 'images_db/images.db'
images_count = 10
LAST_IMAGE_ID_FILE = 'last_image_id.txt'
LAST_EXTRA_IMAGE_ID_FILE = 'last_extra_image_id.txt'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('TRUNCATE TABLE images')
    cursor.execute('TRUNCATE TABLE extra_images')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pin_id INTEGER NOT NULL UNIQUE,
            image_url TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS extra_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pin_id INTEGER NOT NULL UNIQUE,
            image_url TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

def save_last_image_id(last_id, extra=False):
    file_path = LAST_EXTRA_IMAGE_ID_FILE if extra else LAST_IMAGE_ID_FILE
    with open(file_path, 'w') as f:
        f.write(str(last_id))

def get_last_image_id(extra=False):
    file_path = LAST_EXTRA_IMAGE_ID_FILE if extra else LAST_IMAGE_ID_FILE
    try:
        with open(file_path, 'r') as f:
            return int(f.read().strip())
    except FileNotFoundError:
        return 0

def get_images_number(extra=False):
    table_name = 'extra_images' if extra else 'images'
    last_image_id = get_last_image_id(extra)
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(f'SELECT COUNT(*) FROM {table_name} WHERE id > ?', (last_image_id,))
    number_of_images = cursor.fetchone()[0]
    conn.close()
    
    return number_of_images

def get_images_and_last_id(num_images, extra=False):
    table_name = 'extra_images' if extra else 'images'
    last_image_id = get_last_image_id(extra)
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Выбор изображений после последнего полученного ID
    cursor.execute(f'SELECT id, pin_id, image_url FROM {table_name} WHERE id > ? ORDER BY id ASC LIMIT ?', (last_image_id, num_images))
    rows = cursor.fetchall()
    
    remaining_photos = 0
    # Если есть новые изображения, обновляем последний ID
    if rows:
        new_last_image_id = rows[-1][0]
        save_last_image_id(new_last_image_id, extra)

        cursor.execute(f'SELECT COUNT(*) FROM {table_name} WHERE id > ?', (new_last_image_id,))
        remaining_photos = cursor.fetchone()[0]

    conn.close()
    
    return rows, remaining_photos

async def add_images_to_db(bot, extra=False):
    init_db()
    parse_fn = parse_pinterest_non_asian_images if extra else parse_pinterest_images
    image_data = await parse_fn(bot)
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    table_name = 'extra_images' if extra else 'images'
    for image in image_data:
        image_id, image_url = image['pin_id'], image['url']
        
        try:
            cursor.execute(f'INSERT INTO {table_name} (pin_id, image_url) VALUES (?, ?)', (image_id, image_url,))
        except sqlite3.IntegrityError:
            conn.commit()
            conn.close()
            return -1
    
    conn.commit()
    conn.close()
    return 1

async def get_image_by_pin_id(pin_id, extra=False):
    init_db()
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if extra==True:
        cursor.execute(f'SELECT image_url FROM extra_images WHERE pin_id = ?', (pin_id,))
    else:
        cursor.execute(f'SELECT image_url FROM images WHERE pin_id = ?', (pin_id,))
    
    rows = cursor.fetchall()

    conn.close()
    
    return rows[0]