import asyncio
import sqlite3
import os
from pathlib import Path
from playwright.async_api import async_playwright

# Убедитесь, что существует директория для сохранения изображений
VIDEOS_DIR = 'video'
if not os.path.exists(VIDEOS_DIR):
    os.makedirs(VIDEOS_DIR)

# Инициализация БД
DATABASE = 'video_db/approved_videos.db'
video_count = 10
LAST_VIDEO_ID_FILE = 'last_approved_video_id.txt'

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

async def add_video_to_db(video_data):
    init_db()
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    for video in video_data:
        video_id, video_url = video['pin_id'], video['url']
        print(video_id,video_url)
        try:
            cursor.execute('INSERT INTO video (pin_id, video_url) VALUES (?, ?)', (video_id, video_url,))
        except sqlite3.IntegrityError:
            pass
    
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

def get_video(num_video):
    last_video_id = get_last_video_id()
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Выбор изображений после последнего полученного ID
    cursor.execute('SELECT id, pin_id, video_url FROM video WHERE id > ? ORDER BY id ASC LIMIT ?', (last_video_id, num_video))
    rows = cursor.fetchall()

    remaining_photos = 0
    # Если есть новые изображения, обновляем последний ID
    if rows:
        cursor.execute('SELECT COUNT(*) FROM video WHERE id > ?', (last_video_id,))
        remaining_photos = cursor.fetchone()[0]
    
    conn.close()
    
    return rows, remaining_photos

def get_video_and_last_id(num_video):
    last_video_id = get_last_video_id()
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Выбор изображений после последнего полученного ID
    cursor.execute('SELECT id, pin_id, video_url FROM video WHERE id > ? ORDER BY id ASC LIMIT ?', (last_video_id, num_video))
    rows = cursor.fetchall()
    
    remaining_photos = 0
    # Если есть новые изображения, обновляем последний ID
    if rows:
        new_last_video_id = rows[-1][0]
        save_last_video_id(new_last_video_id)

        cursor.execute('SELECT COUNT(*) FROM video WHERE id > ?', (new_last_video_id,))
        remaining_photos = cursor.fetchone()[0]

    conn.close()
    
    return rows, remaining_photos
