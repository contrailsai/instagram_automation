import asyncio
from playwright.async_api import async_playwright, Page, Locator
from dotenv import load_dotenv
from reels_scroller.Instargam_Automater import Instagram_Automator
from database import get_scraper_data_by_id, set_scraper_activity, get_freq_stats, create_freq_stats, profiles_with_links, update_profile_data

load_dotenv()

async def main(scraper_id: str):
    status = False
    # print("starting new scraper with id:", scraper_id)
    scraper_data = await get_scraper_data_by_id(scraper_id)

    # freq stats
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

    print("starting scraper: ", scraper_data["text"])

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

            page2 = await browser.new_page()

            profiles_link_data = await profiles_with_links(scraper_id)

            for profile in profiles_link_data:
                
                is_suspicious = False
                for link in profile["links"]:
                    is_suspicious = is_suspicious or await check_if_suspicious_link(page2, link)

                await update_profile_data(profile["username"], {"is_suspicious": is_suspicious})

            # instagram automator
            page1 = await browser.new_page()

            status = True
            await set_scraper_activity(scraper_id, True)
            iao = Instagram_Automator(page1, scraper_data)
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

async def check_if_suspicious_link(page: Page, link: str):
    try:
        # Validate the link format
        if not link.startswith("http://") and not link.startswith("https://"):
            print(f"Invalid URL format: {link}")
            return False

        # Navigate to the link with a delay
        await page.goto(link, timeout=30000)  # Increased timeout to handle slow-loading pages
        await asyncio.sleep(3)  # Adding a delay to avoid going too fast
        content = await page.content()
        suspicious_keywords = ["win cash", "real money", "fantasy betting", "gambling", "casino", "betting", "wager", "poker", "lottery"]
        
        if any(keyword in content.lower() for keyword in suspicious_keywords):
            print(f"Suspicious link detected: {link}")
            return True
        else:
            print(f"Link is safe: {link}")
            return False
    except Exception as e:
        print(f"Error checking link {link}: {str(e)}")

if __name__ == '__main__':
    asyncio.run(main())