import asyncio
import sqlite3
import os
from pathlib import Path
from playwright.async_api import async_playwright

# Убедитесь, что существует директория для сохранения изображений
IMAGES_DIR = 'images'
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

# Инициализация БД
DATABASE = 'images_db/approved_images.db'
images_count = 10
LAST_IMAGE_ID_FILE = 'last_approved_image_id.txt'

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

async def add_images_to_db(image_data):
    init_db()
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    for image in image_data:
        image_id, image_url = image['pin_id'], image['url']
        print(image_id,image_url)
        try:
            cursor.execute('INSERT INTO images (pin_id, image_url) VALUES (?, ?)', (image_id, image_url,))
        except sqlite3.IntegrityError:
            pass
    
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

def get_images(num_images):
    last_image_id = get_last_image_id()
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Выбор изображений после последнего полученного ID
    cursor.execute('SELECT id, pin_id, image_url FROM images WHERE id > ? ORDER BY id ASC LIMIT ?', (last_image_id, num_images))
    rows = cursor.fetchall()

    remaining_photos = 0
    # Если есть новые изображения, обновляем последний ID
    if rows:
        cursor.execute('SELECT COUNT(*) FROM images WHERE id > ?', (last_image_id,))
        remaining_photos = cursor.fetchone()[0]
    
    conn.close()
    
    return rows, remaining_photos

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
