from playwright.async_api import async_playwright
from images_db.hot_images import insert_images


def convert_urls_to_dict(url_list, name):
    return {name: url for url in url_list}

async def scrape_photos(context, page):
    photo_urls = []
    photo_items = await page.query_selector_all("div.photo-item a")
    
    for item in photo_items:
        href = await item.get_attribute('href')
        if href:
            new_page = await context.new_page()
            
            await new_page.goto('https://www.topfapgirlspics.com'+href)
            
            await new_page.wait_for_load_state('networkidle')
            
            img_element = await new_page.query_selector("div.img a img")
            if img_element:
                src = await img_element.get_attribute('src')
                if src:
                    photo_urls.append(src)
                    print(src)

            await new_page.close()
        
    return photo_urls

async def scrape_all_pages(id, name):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        context.set_default_navigation_timeout(60000)
        page = await context.new_page()

        await page.goto(f"https://www.topfapgirlspics.com/{id}/")
        await page.wait_for_load_state('networkidle')

        all_photo_urls = []
        page_num = 0
        while True:
            photo_urls = await scrape_photos(context, page)
            all_photo_urls.extend(photo_urls)

            print(photo_urls, page_num)
            page_num += 1

            next_button = await page.query_selector('div.pagination a:has-text("Next")')
            if not next_button:
                break

            await next_button.click()

            await page.wait_for_load_state('networkidle')
        
        await browser.close()
        insert_images(all_photo_urls, id, name)
        