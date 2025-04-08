import asyncio
from playwright.async_api import async_playwright, Page, Locator
# from authentication import signIn
# from reels_scroller import reels_scroller, profile_reels_watcher
# from utils import save_profile_data
from dotenv import load_dotenv
from Instargam_Automater import Instagram_Automator

load_dotenv()

async def main():
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

            iao = Instagram_Automator(page)
            await iao.loop_runner()
            
            print("Closing browser...")
            await browser.close()
        except Exception as e:
            print(f"Error in loop_runner: {str(e)}")
            # await self.browser.close()

if __name__ == '__main__':
    asyncio.run(main())