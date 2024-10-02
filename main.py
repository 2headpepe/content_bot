import asyncio
from bot import init_bot
from images_db.db import (
    get_images_and_last_id, 
    add_images_to_db
)
# async def main():
#     await init_bot()

# if __name__ == "__main__":
#     asyncio.run(main())

# server.py
from flask import Flask, request, jsonify

app = Flask(__name__)

# Предположим, у вас есть список изображений
# images = ["url1.jpg", "url2.jpg", "url3.jpg"]



@app.route('/api/images', methods=['GET'])
def get_images():
    return jsonify({"images": images})

@app.route('/api/like', methods=['POST'])
def like_image():
    data = request.json
    print('Liked:', data.get('image'))
    return '', 200

@app.route('/api/dislike', methods=['POST'])
def dislike_image():
    data = request.json
    print('Disliked:', data.get('image'))
    return '', 200

if __name__ == '__main__':
    await add_images_to_db()
    media_data, images = get_images_and_last_id(3)
    app.run(debug=True)