import asyncio
import sqlite3
import os
from pathlib import Path
from playwright.async_api import async_playwright
from pinterest_parser import parse_basketball_video

# Убедитесь, что существует директория для сохранения изображений
IMAGES_DIR = 'video'
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

# Инициализация БД
DATABASE = 'video_db/images.db'
images_count = 10
LAST_VIDEO_ID_FILE = 'video_db/last_video_id.txt'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS video (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pin_id INTEGER NOT NULL,
            video_url TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

def save_last_video_id(last_id):
    with open(LAST_VIDEO_ID_FILE, 'w') as f:
        f.write(str(last_id))

def get_last_video_id():
    try:
        with open(LAST_VIDEO_ID_FILE, 'r') as f:
            return int(f.read().strip())
    except FileNotFoundError:
        return 0

def get_images_number():
    last_video_id = get_last_video_id()
    
    cursor.execute('SELECT id, pin_id, video_url FROM video WHERE id > ? ORDER BY id ASC', (last_video_id))
    return cursor.fetchone()[0]
    
def get_video_and_last_id(num_video):
    last_video_id = get_last_video_id()
    print(last_video_id)
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Выбор изображений после последнего полученного ID
    cursor.execute('SELECT id, pin_id, video_url FROM video WHERE id > ? ORDER BY id ASC LIMIT ?', (last_video_id, num_video))
    rows = cursor.fetchall()
    
    remaining_video = 0
    # Если есть новые изображения, обновляем последний ID
    if rows:
        new_last_video_id = rows[-1][0]
        save_last_video_id(new_last_video_id)

        cursor.execute('SELECT COUNT(*) FROM video WHERE id > ?', (new_last_video_id,))
        remaining_video = cursor.fetchone()[0]

    conn.close()
    
    return rows, remaining_video

async def add_video_to_db():
    init_db()
    video_data = await parse_basketball_video()
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    for video in video_data:
        video_id, video_url = video['pin_id'], video['url']
        
        try:
            cursor.execute('INSERT INTO video (pin_id, video_url) VALUES (?, ?)', (video_id, video_url,))
        except sqlite3.IntegrityError:
            conn.commit()
            conn.close()
            return -1
            pass
    
    conn.commit()
    conn.close()
    return 1

async def get_video_by_pin_id(pin_id):
    init_db()
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('SELECT video_url FROM video WHERE pin_id = ?', (pin_id,))
    rows = cursor.fetchall()
    return rows[0]
