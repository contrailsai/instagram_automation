import asyncio
from playwright.async_api import async_playwright, Page, Locator
from authentication import signIn
from dotenv import load_dotenv
import json
import time
import os

from reels_scroller import reels_scroller, profile_reels_watcher

load_dotenv()

def save_profile_data(bio_data):
    filepath = "profiles_links_n_text.json"
    usernames_bio = dict()

    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            usernames_bio = json.load(f)
        
    usernames_bio.update(bio_data)

    with open(filepath, 'w') as f:
        json.dump(usernames_bio, f)

async def watch_reels(page: Page, usernames):
    # Create a shared data object to store network responses
    reels_data = {}

    topic_texts = ["ipl", "rcb", "gt", "csk", "dc", "kkr", "rr", "pk", "lsg", "srh", "mi", "cricket"]

    # Setup network listener
    page.on("response", lambda response: handle_reels_network(response, reels_data))

    INSTAGRAM_REELS_URL = "https://www.instagram.com/reels"
    await page.goto(INSTAGRAM_REELS_URL)

    try:
        while len(reels_data.keys()) == 0:
            await asyncio.sleep(1)

        await reels_scroller(page, reels_data, topic_texts, usernames)
    except:
        input("stopped reels scrolling (waiting for a key to exit)")

async def extract_links_from_bios(page: Page, usernames:set):

    # with open("potential_profiles_list.txt", 'r') as f:
    #     unique_usernames = {line.strip() for line in f if line.strip()}
    
    unique_usernames = list(usernames)
    
    bio_data = dict()

    page.on("response", lambda response: handle_profile_network(response, bio_data))

    for username in unique_usernames:
        PROFILE_URL = f"https://www.instagram.com/{username}"
        await page.goto(PROFILE_URL)
        await page.wait_for_timeout(3*1000) # wait 3 secs for page to load
        start_time = time.time()
        while (not bio_data.get(username, False)) or (time.time()-start_time > 24) : # max wait for 24 secs (in case profile doesn't exist anymore / its private)
            await page.wait_for_timeout(1000) # wait 1 sec before rechecking

        await page.wait_for_timeout(3*1000) # avoid sudden shifts to different profiles (min 6 secs on a profile)

    save_profile_data(bio_data)

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

        # await page.wait_for_timeout(30*60*1000)
        start_time = time.time()
        usernames = set()

        while time.time()-start_time < 4*60*60:
            await watch_reels(page, usernames)
            await extract_links_from_bios(page, usernames)

            usernames.clear()
            
        # # to watch reels from /reels
        # await watch_reels(page)

        # # to watch reels from a profile  (profile)   (watch for 2 hrs)    (watch 1 for 2 mins)
        # await profile_reels_watcher(page, "ipl20", timer_to_stop=2*60*60, time_to_watch_1=2*60)

        # extract links from username's bio saved in text file post func "watch_reels".

        print("Closing browser...")
        await browser.close()

async def handle_profile_network(response, bio_data):
    url = response.url
    target_url = "https://www.instagram.com/graphql/query"

    if target_url in url:
        try:
            response_data = await response.json()
            if response_data["data"].get("user", False):


                new_bio_data = dict()
                username = response_data["data"]["user"]["username"]
                bio_txt = response_data["data"]["user"]["biography"]
                bio_links = []

                for link_obj in response_data["data"]["user"]["bio_links"]: 
                    bio_links.append( link_obj["url"] )
                
                new_bio_data[username] = {"username": username, "links": bio_links, "text": bio_txt}

                bio_data.update(new_bio_data)

        except Exception as e:
            print(f"Failed to process response from {url}: {str(e)}")


async def handle_reels_network(response, reels_data):
    """Process network responses and store relevant data"""
    
    url = response.url
    
    target_url = "https://www.instagram.com/graphql/query"
    # target_url = ""

    # Check if this is the URL we're interested in
    if target_url in url:
        try:
            response_data = await response.json()

            # if response_data["data"].get("xdt_api__v1__clips__user__connection_v2", False) :
            #     print(f"Found new reels update request")

            #     new_reels_data = {}

            #     for edge in response_data["data"]["xdt_api__v1__clips__user__connection_v2"]["edges"]:
            #         media = edge["node"]["media"]
            #         new_reels_data[ media["code"] ] = media
            
            #     reels_data.update(new_reels_data)
    
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