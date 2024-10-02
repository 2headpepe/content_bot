from playwright.async_api import async_playwright
from images_db.hot_images import insert_images
from consts import feedback_chat_id

def convert_urls_to_dict(url_list, name):
    return {name: url for url in url_list}

async def scrape_photos(context, page, bot):
    photo_urls = []
    photo_items = await page.query_selector_all(".model-photo div.photo-item a:not(:has(span))")
    for item in photo_items:
        href = await item.get_attribute('href')
        if href:
            new_page = await context.new_page()
            try:
                await new_page.goto('https://www.topfapgirlspics.com' + href)
                await new_page.wait_for_selector("div.img a img")
                    
                img_element = await new_page.query_selector("div.img a img")
                if img_element:
                    src = await img_element.get_attribute('src')
                    if src:
                        photo_urls.append(src)
                        await bot.send_message(feedback_chat_id, f"{src}")
            except Exception as e:
                await bot.send_message(feedback_chat_id, f"Error occurred: {e}")
            finally:
                await new_page.close()
        
    return photo_urls

async def scrape_all_pages(id, name, bot):
    async with async_playwright() as p:
        retry_attempts = 3  # Number of retry attempts

        for attempt in range(retry_attempts):
            try:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                    '--disable-gpu',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-setuid-sandbox',
                    '--disable-software-rasterizer'
                    ]
                )
                context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36")
                context.set_default_navigation_timeout(120000)
                page = await context.new_page()
                await page.goto(f"https://www.topfapgirlspics.com/{id}/")
        
                await page.wait_for_load_state('networkidle')

                all_photo_urls = []
                while True:
                    photo_urls = await scrape_photos(context, page, bot)
                    all_photo_urls.extend(photo_urls)

                    next_button = await page.query_selector('div.pagination a:has-text("Next")')
                    if not next_button:
                        break

                    await next_button.click()

                    await page.wait_for_load_state('networkidle')
                insert_images(all_photo_urls, id, name)
                break
            except Exception as e:
                if attempt < retry_attempts - 1:
                    await bot.send_message(feedback_chat_id, f"Attempt {attempt + 1} failed. Retrying...")
                else:
                    await bot.send_message(feedback_chat_id, f"Error occurred: {e}")
            finally:
                await browser.close()
