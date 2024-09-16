import asyncio
import sqlite3
import os
from pathlib import Path
from playwright.async_api import async_playwright
from pinterest_parser import parse_pinterest_images

# Убедитесь, что существует директория для сохранения изображений
IMAGES_DIR = 'images'
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

# Инициализация БД
DATABASE = 'images_db/images.db'
images_count = 10
LAST_IMAGE_ID_FILE = 'last_image_id.txt'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pin_id INTEGER NOT NULL,
            image_url TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

def save_last_image_id(last_id):
    with open(LAST_IMAGE_ID_FILE, 'w') as f:
        f.write(str(last_id))

def get_last_image_id():
    try:
        with open(LAST_IMAGE_ID_FILE, 'r') as f:
            return int(f.read().strip())
    except FileNotFoundError:
        return 0

def get_images_number():
    last_image = get_last_image_id()
    
    cursor.execute('SELECT id, pin_id, image_url FROM images WHERE id > ? ORDER BY id ASC', (last_image_id))
    return cursor.fetchone()[0]
    
def get_images_and_last_id(num_images):
    last_image_id = get_last_image_id()
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Выбор изображений после последнего полученного ID
    cursor.execute('SELECT id, pin_id, image_url FROM images WHERE id > ? ORDER BY id ASC LIMIT ?', (last_image_id, num_images))
    rows = cursor.fetchall()
    
    remaining_photos = 0
    # Если есть новые изображения, обновляем последний ID
    if rows:
        new_last_image_id = rows[-1][0]
        save_last_image_id(new_last_image_id)

        cursor.execute('SELECT COUNT(*) FROM images WHERE id > ?', (new_last_image_id,))
        remaining_photos = cursor.fetchone()[0]

    conn.close()
    
    return rows, remaining_photos

async def add_images_to_db():
    init_db()
    image_data = await parse_pinterest_images()
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    for image in image_data:
        image_id, image_url = image['pin_id'], image['url']
        
        try:
            cursor.execute('INSERT INTO images (pin_id, image_url) VALUES (?, ?)', (image_id, image_url,))
        except sqlite3.IntegrityError:
            conn.commit()
            conn.close()
            return -1
            pass
    
    conn.commit()
    conn.close()
    return 1

async def get_image_by_pin_id(pin_id):
    init_db()
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('SELECT image_url FROM images WHERE pin_id = ?', (pin_id,))
    rows = cursor.fetchall()
    return rows[0]
