import asyncio
from playwright.async_api import async_playwright, Page, Locator
from dotenv import load_dotenv
from reels_scroller.Instargam_Automater import Instagram_Automator

from server.database.scrapers import get_scraper_data_by_id, set_scraper_activity, get_freq_stats, create_freq_stats
from server.database.links import get_links_data, update_link_data, get_links_to_check
from server.database.profiles import  profiles_with_links, update_profile_data
from server.database.ads import update_ad_data, get_all_non_filtered_ads

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

            # genai.configure(api_key=llm_api_key)
            # llm_model = genai.GenerativeModel(model_name='gemini-2.0-flash')
            
            #--------------------------------------------------------------
            # # GO THROUGH PROFILES WEBSITES
            # page2 = await browser.new_page()

            # # profiles_link_data = await profiles_with_links(scraper_id)
            # links_data = await get_links_to_check(scraper_id)
            # # links_data = await get_links_data(scraper_id)

            # for link_data in links_data:
            #     resp = await check_if_suspicious_link(page2, link_data["link"], scraper_data, llm_model)
            #     update_data = dict({
            #         "suspicious": resp["is_relevant"],
            #         "screenshot": resp["screenshot_base64"]
            #     })
            #     print("link_data = ", link_data)
            #     await update_link_data(link_data["id"], update_data)

            # -------------------------------------------------------------
            # # # GO THROUGH ADS WEBSITES
            # page3 = await browser.new_page()
            # ads = await get_all_non_filtered_ads(scraper_id)

            # for ad in ads:
            #     resp = await check_sus_filter_links(page3, ad["link"], scraper_data, llm_model)
            #     await update_ad_data(ad["id"], {
            #         "filtered_link": resp["filtered_link"],
            #         "screenshot": resp["screenshot_base64"],
            #         "suspicious": resp["is_relevant"]
            #     })
            #--------------------------------------------------------------

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

async def check_sus_filter_links(page: Page, link: str, scraper_data: dict, llm_model: GenerativeModel) -> dict:
    try:
        # Validate the link format
        if not link.startswith("http://") and not link.startswith("https://"):
            print(f"Invalid URL format: {link}")
            return {"is_relevant": False, "screenshot_base64": None, "filtered_link": False}

        # Navigate with a timeout but handle it explicitly
        try:
            await page.goto(link, wait_until="domcontentloaded", timeout=30000)
        except TimeoutError:
            print(f"Page load timed out for {link}, but continuing anyway")
        
        # Wait for the page to stabilize
        await page.wait_for_timeout(5000)
        
        url = page.url
        # Check if we have any content before proceeding
        body_present = await page.locator("body").count() > 0
        
        if not body_present:
            print(f"No body element found on {link}")
            return {"is_relevant": False, "screenshot_base64": None}

        # Extract Content from the page for llm
        title = await page.title()
        
        # Safely get meta description
        meta_description = ""
        try:
            meta = await page.query_selector("meta[name='description']")
            if meta:
                meta_description = await meta.get_attribute("content") or ""
        except Exception:
            pass

        # Safely get headings
        headings_text = ""
        try:
            headings = await page.locator("h1, h2, h3").all_inner_texts()
            headings_text = " | ".join(headings)
        except Exception:
            pass

        # Safely get body text preview
        body_preview = ""
        try:
            body_text = await page.locator("body").inner_text()
            body_preview = body_text[:1500]  # Limit tokens
        except Exception:
            pass

        content = f"""
                Title: {title}
                Meta Description: {meta_description}
                Headings: {headings_text}
                Body Preview: {body_preview}
                """

        # Take a screenshot and encode it in base64
        screenshot_bytes = await page.screenshot(type="jpeg")
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

        # Perform relevancy check using LLM
        response = await website_relevancy_check(llm_model, content, scraper_data["text"])

        return {"is_relevant": response, "screenshot_base64": screenshot_base64, "filtered_link": url}

        
    except Exception as e:
        print(f"Error checking link {link}: {str(e)}")
        return {"is_relevant": False, "screenshot_base64": None, "filtered_link": url}

async def check_if_suspicious_link(page: Page, link: str, scraper_data: dict, llm_model: GenerativeModel) -> dict:
    try:
        # Validate the link format
        if not link.startswith("http://") and not link.startswith("https://"):
            print(f"Invalid URL format: {link}")
            return {"is_relevant": False, "screenshot_base64": None}

        # Navigate with a timeout but handle it explicitly
        try:
            await page.goto(link, wait_until="domcontentloaded", timeout=30000)
        except TimeoutError:
            print(f"Page load timed out for {link}, but continuing anyway")
            # Continue execution even after timeout
            
        # Wait for the page to stabilize
        await page.wait_for_timeout(5000)
        
        # Check if we have any content before proceeding
        body_present = await page.locator("body").count() > 0
        
        if not body_present:
            print(f"No body element found on {link}")
            return {"is_relevant": False, "screenshot_base64": None}

        # Extract Content from the page for llm
        title = await page.title()
        
        # Safely get meta description
        meta_description = ""
        try:
            meta = await page.query_selector("meta[name='description']")
            if meta:
                meta_description = await meta.get_attribute("content") or ""
        except Exception:
            pass

        # Safely get headings
        headings_text = ""
        try:
            headings = await page.locator("h1, h2, h3").all_inner_texts()
            headings_text = " | ".join(headings)
        except Exception:
            pass

        # Safely get body text preview
        body_preview = ""
        try:
            body_text = await page.locator("body").inner_text()
            body_preview = body_text[:1500]  # Limit tokens
        except Exception:
            pass

        content = f"""
                Title: {title}
                Meta Description: {meta_description}
                Headings: {headings_text}
                Body Preview: {body_preview}
                """

        # Take a screenshot and encode it in base64
        screenshot_bytes = await page.screenshot(type="jpeg")
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

        # Perform relevancy check using LLM
        response = await website_relevancy_check(llm_model, content, scraper_data["text"])

        return {"is_relevant": response, "screenshot_base64": screenshot_base64}

    except Exception as e:
        print(f"Error checking link {link}: {str(e)}")
        return {"is_relevant": False, "screenshot_base64": None}
    
if __name__ == '__main__':
    asyncio.run(main())