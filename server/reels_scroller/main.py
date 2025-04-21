import asyncio
from playwright.async_api import async_playwright, Page, Locator
from dotenv import load_dotenv
from reels_scroller.Instargam_Automater import Instagram_Automator
from database import get_scraper_data_by_id, set_scraper_activity, get_freq_stats, create_freq_stats

load_dotenv()

async def main(scraper_id: str):
    status = False
    print("starting new scraper with id:", scraper_id)
    scraper_data = await get_scraper_data_by_id(scraper_id)

    try:
        scraper_stats = await get_freq_stats(scraper_id)
        print("scraper_stats =", scraper_stats)
        if scraper_stats == None:
            raise "not found"
        scraper_data["topic_stats"] = scraper_stats
    except:
        # print("ERROR--------> ", e)
        
        # did not exsit then create it 
        new_scraper_stats = dict({
            "scraper_id": scraper_id,
            "freq": dict(),
            "priority": dict()
        })
        for topic in scraper_data["topic_attributes"]:
            new_scraper_stats["freq"][topic.lower()] = 0
            new_scraper_stats["priority"][topic.lower()] = 0

        await create_freq_stats(new_scraper_stats)
        scraper_data["topic_stats"] = new_scraper_stats

    print("starting scraper ", scraper_data["text"])

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

            status = True
            await set_scraper_activity(scraper_id, True)
            iao = Instagram_Automator(page, scraper_data)
            await iao.loop_runner()
            
            print("Closing browser...")
            await browser.close()
        except Exception as e:
            print(f"Error in loop_runner: {str(e)}")
            await set_scraper_activity(scraper_id, False)
            status = False
            # await self.browser.close()
    if status:
        await set_scraper_activity(scraper_id, False)
        status = False

if __name__ == '__main__':
    asyncio.run(main())