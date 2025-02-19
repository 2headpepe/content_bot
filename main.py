import asyncio
from bot import init_bot, bot
from images_db.db import (
    get_images_and_last_id, 
    add_images_to_db
)
# from generate_image import get_image
from parse_topfapgirls import scrape_all_pages

async def main():
    await init_bot()
    # await get_image()

if __name__ == "__main__":
    asyncio.run(main())
