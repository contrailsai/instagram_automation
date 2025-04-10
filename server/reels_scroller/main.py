import asyncio
from playwright.async_api import async_playwright, Page, Locator
from dotenv import load_dotenv
from reels_scroller.Instargam_Automater import Instagram_Automator
from database import get_document_by_id

load_dotenv()

async def main(scraper_id: str):
    print("starting new scraper with id:", scraper_id)
    scraper_data = await get_document_by_id(scraper_id)
    print("scraper_data = ", scraper_data)
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                channel="chrome",
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--use-angle=gl',
                    '--enable-webgl',
                    '--disable-dev-shm-usage'
                ]
            )
            page = await browser.new_page()

            iao = Instagram_Automator(page, scraper_data)
            await iao.loop_runner()
            
            print("Closing browser...")
            await browser.close()
        except Exception as e:
            print(f"Error in loop_runner: {str(e)}")
            # await self.browser.close()

if __name__ == '__main__':
    asyncio.run(main())