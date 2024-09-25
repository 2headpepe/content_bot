import sqlite3
import random

DATABASE = 'images_db/hot_images.db'

def create_database():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS images (
            auto_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            id TEXT NOT NULL,
            url TEXT NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS girl_images (
            id TEXT PRIMARY KEY,
            name TEXT,
            last_image_id TEXT DEFAULT '0',
            FOREIGN KEY (last_image_id) REFERENCES images (id)
        )
    ''')

    conn.commit()
    conn.close()

def insert_images(images, id, name):
    create_database()
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.executemany('INSERT INTO images (id, name, url) VALUES (?, ?, ?)', [(id, name, url) for url in images])
    c.execute('''
        INSERT INTO girl_images (id, name) 
        VALUES (?, ?) 
        ON CONFLICT(id) 
        DO NOTHING
    ''', (id, name))
    
    conn.commit()
    conn.close()

def set_last_image_id(girl_id, new_last_image_id, name):
    create_database()

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('REPLACE INTO girl_images (id, name, last_image_id) VALUES (?, ?, ?)', (girl_id, name, new_last_image_id))
    conn.commit()
    conn.close()
    
def get_random_girl():
    create_database()

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT id, name FROM girl_images')
    row = c.fetchall()
    conn.commit()
    conn.close()

    return random.choice(row)

def get_new_images(girl_id, limit, name):
    create_database()

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute('SELECT last_image_id FROM girl_images WHERE id = ?', (girl_id,))
    row = c.fetchone()
    last_image_id = row[0] if row else '0'

    if last_image_id == '0':
        c.execute('SELECT auto_id, id, url FROM images WHERE id = ? ORDER BY auto_id  LIMIT ?', (girl_id, limit,))
    else:
        c.execute('SELECT auto_id, id, url FROM images WHERE auto_id > ? and id = ? ORDER BY auto_id LIMIT ?', (last_image_id,girl_id, limit))

    new_images = c.fetchall()
    
    if new_images:
        new_last_image_id = new_images[-1][0]
        print('REPLACE INTO girl_images (id, name, last_image_id) VALUES (?, ?, ?)', (girl_id, name, new_last_image_id))
        c.execute('REPLACE INTO girl_images (id, name, last_image_id) VALUES (?, ?, ?)', (girl_id, name, new_last_image_id))
    
    conn.commit()
    conn.close()

    return [url for _,_, url in new_images]

def get_random_girl_images(limit):
    id, name = get_random_girl()    

    images = get_new_images(id, limit, name)

    return images, name
