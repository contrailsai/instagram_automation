import asyncio
from playwright.async_api import async_playwright, Page, Locator
from authentication import signIn
from dotenv import load_dotenv
import json
import time

from reels_scroller import reels_scroller

load_dotenv()

async def main():
    async with async_playwright() as p:
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
        await signIn(page, browser)

        # Create a shared data object to store network responses
        reels_data = {}
        
        # Setup network listener
        page.on("response", lambda response: handle_network(response, reels_data))

        INSTAGRAM_REELS_URL = "https://www.instagram.com/reels"
        await page.goto(INSTAGRAM_REELS_URL)

        try:
            while len(reels_data.keys()) == 0:
                await asyncio.sleep(1)

            await reels_scroller(page, reels_data)
        except:
            input("stopped reels scrolling (waiting for a key to exit)")

        print("Closing browser...")
        await browser.close()

async def handle_network(response, reels_data):
    """Process network responses and store relevant data"""
    
    url = response.url
    target_url = "https://www.instagram.com/graphql/query"
    
    # Check if this is the URL we're interested in
    if target_url in url:
        try:
            # Store the response data in our shared object
            response_data = await response.json()

            if response_data["data"].get("xdt_api__v1__clips__home__connection_v2", False) :
                print(f"Found new reels update request")
                
                new_reels_data = {}
                for edge in response_data["data"]["xdt_api__v1__clips__home__connection_v2"]["edges"]:
                    media = edge["node"]["media"]
                    new_reels_data[ media["code"] ] = media

                reels_data.update(new_reels_data)

                # Save to all reels content as json
                import os
                os.makedirs("network", exist_ok=True)
                with open(f"network/reels_feed_data.json", 'w') as f:
                    json.dump(reels_data , f)
            
        except Exception as e:
            print(f"Failed to process response from {url}: {str(e)}")

if __name__ == '__main__':
    asyncio.run(main())