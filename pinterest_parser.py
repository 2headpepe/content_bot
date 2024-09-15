import asyncio
from playwright.async_api import async_playwright
import re
from consts import pinterest_login, pinterest_password

async def try_login(p):
    browser = await p.chromium.launch(headless=False)
    context = await browser.new_context(
            locale='ru-RU',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    )
    page = await context.new_page()

    # Navigate to Pinterest login page
    await page.goto('https://ru.pinterest.com/login/')

    # Log into Pinterest
    await page.fill('input[name="id"]', pinterest_login)
    await page.fill('input[name="password"]', pinterest_password)
    await page.click('button[type="submit"]')

    # Wait for the feed page to load completely
    await page.wait_for_load_state('load')
    # Add a delay to ensure all images are loaded
    await page.wait_for_timeout(5000)

    return browser, page

def transform_image_url(url):
    # Используем регулярное выражение для поиска любой части с размером (например, '564x', '236x', и т.д.) и заменяем его на "originals".
    pattern = r"(https://i\.pinimg\.com/)\d+x/"
    replacement = r"\1originals/"
    
    # Замена указанного паттерна в URL
    new_url = re.sub(pattern, replacement, url)
    
    return new_url

async def parse_pinterest_images():
    async with async_playwright() as p:
        browser, page = await try_login(p)
        # Scroll down to ensure more images are loaded
        await page.evaluate('window.scrollBy(0, window.innerHeight * 2)')
        await page.wait_for_timeout(2000)  # Wait for loading

        # Scrape the image URLs and pin IDs
        pins = await page.evaluate('''() => {
        const images = document.querySelectorAll('img[srcset]');
            const result = [];
        images.forEach(img => {
            const parent = img.closest('a[href*="/pin/"]');
            if (parent) {
                const pinId = parent.href.split("/pin/")[1].split("/")[0];
                result.push({id: pinId, url: img.src});
            }
        });
        return result.slice(0, 30);
        }''')

        await browser.close()

        return [{'pin_id': pin['id'], 'url': transform_image_url(pin['url'])} for i, pin in enumerate(pins)]

async def like_pin(page, pin_id):
    pin_url = f"https://ru.pinterest.com/pin/{pin_id}/"
    await page.goto(pin_url)
    await page.wait_for_timeout(3000)  # Ждем загрузку страницы пина

    await page.click("button:has-text('Сохранить')")

    await page.wait_for_timeout(2000)  # Короткая задержка после каждого действия

async def like_pins(pins):
    async with async_playwright() as p:
        browser, page = await try_login(p)
        for id, url in pins:
            await like_pin(page, id)
        await browser.close()