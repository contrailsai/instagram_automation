import asyncio
from playwright.async_api import async_playwright, Page, Locator
from dotenv import load_dotenv
from reels_scroller.Instargam_Automater import Instagram_Automator
from database import get_scraper_data_by_id, set_scraper_activity, get_freq_stats, create_freq_stats, get_links_data, update_link_data, profiles_with_links, update_profile_data
import os 
from google import generativeai as genai
from google.generativeai import GenerativeModel
from llm_instructions import website_relevancy_check
import base64
from io import BytesIO


llm_api_key = os.getenv("GENAI_API_KEY")

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

            # # GO THROUGH WEBSITES
            # page2 = await browser.new_page()

            # # profiles_link_data = await profiles_with_links(scraper_id)
            # links_data = await get_links_data(scraper_id)

            # genai.configure(api_key=llm_api_key)
            # llm_model = genai.GenerativeModel(model_name='gemini-2.0-flash')
            
            # for link_data in links_data:
            #     resp = await check_if_suspicious_link(page2, link_data["link"], scraper_data, llm_model)
            #     update_data = dict({
            #         "suspicious": resp["is_relevant"],
            #         "screenshot": resp["screenshot_base64"],
            #     })
            #     print("link_data = ", link_data)
            #     await update_link_data(link_data["id"], update_data)

            
            # Instagram Automator
            page1 = await browser.new_page()

            status = True
            await set_scraper_activity(scraper_id, True)
            iao = Instagram_Automator(page1, scraper_data)
            await iao.loop_runner()
            
            print("Closing browser...")
            await browser.close()
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error in loop_runner: {str(e)}")
            await set_scraper_activity(scraper_id, False)
            status = False
            # await self.browser.close()
    if status:
        await set_scraper_activity(scraper_id, False)
        status = False

async def check_if_suspicious_link(page: Page, link: str, scraper_data: dict, llm_model: GenerativeModel) -> dict:
    try:
        # Validate the link format
        if not link.startswith("http://") and not link.startswith("https://"):
            print(f"Invalid URL format: {link}")
            return {"is_relevant": False, "screenshot_base64": None}

        # Navigate to the link with a delay
        await page.goto(link, timeout=30000)  # Increased timeout to handle slow-loading pages
        await asyncio.sleep(3)  # Adding a delay to avoid going too fast
        # content = await page.content()

        # Extract Content from the page for llm
        title = await page.title()
        # Meta description
        meta = await page.query_selector("meta[name='description']")
        meta_description = await meta.get_attribute("content") if meta else ""

        # meta_description = await page.locator("meta[name='description']").get_attribute("content")
        # if not meta_description:
        #     meta_description = ""

        # Headings
        headings = await page.locator("h1, h2, h3").all_inner_texts()
        headings_text = " | ".join(headings)

        # Body text preview
        body_text = await page.locator("body").inner_text()
        body_preview = body_text[:1500]  # Limit tokens

        content = f"""
                Title: {title}
                Meta Description: {meta_description}
                Headings: {headings_text}
                Body Preview: {body_preview}
                """

        # Perform relevancy check using LLM
        response = await website_relevancy_check(llm_model, content, scraper_data["text"])

        # Take a screenshot and encode it in base64
        screenshot_bytes = await page.screenshot(type="jpeg")
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

        return {"is_relevant": response, "screenshot_base64": screenshot_base64}

    except Exception as e:
        print(f"Error checking link {link}: {str(e)}")
        return {"is_relevant": False, "screenshot_base64": None}

if __name__ == '__main__':
    asyncio.run(main())