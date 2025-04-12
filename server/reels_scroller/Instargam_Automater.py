import asyncio
import json
import os
import time
from pathlib import Path
from playwright.async_api import Page, Browser, Response
from typing import Optional
from playwright.async_api import async_playwright, Page, Locator

from database import update_scraper_data, get_account_by_scraper_id, save_new_auth, save_scraped_content, add_profile, update_profile, get_unscraped_profiles
from reels_scroller.utils import save_profile_data
import base64

class Instagram_Automator:
    def __init__(self, page: Page, scraper_data):
        self.loop_watch_time = 2*60*60  # 2 hours
        self.usernames = set()
        self.page: Page = page
        self.scraper_data = scraper_data
        self.id = scraper_data.get("id", None)
        self.reels_seen = scraper_data.get("reels_seen", 0)
        self.relevant_reels_seen = scraper_data.get("relevant_reels_seen", 0)
        self.total_time = scraper_data.get("total_time", 0)

        # [search, profile_reels, reels, profile_bio, stopped, suspended]
        self.state = scraper_data.get("state", "new")

        self.topics = set()
        for topic in scraper_data.get("topic_attributes", []):
            topic_elements = topic.split(" ")
            for topic_element in topic_elements:
                self.topics.add(topic_element)

        self.topics_list : list[str] = list(self.topics)
        self.hashtags : list[str] = scraper_data.get("hashtags", [])

# login based on username, password in env or the auth cookies in the json file
    async def signIn(self) -> bool:
        account_data: dict = await get_account_by_scraper_id(self.id)

        # AUTH_FILE = Path("ig_auth.json")
        INSTAGRAM_AUTH_URL = "https://www.instagram.com/accounts/login/"
        INSTAGRAM_HOME_URL = "https://www.instagram.com/"
        # Decode username and password from base64
        IG_USERNAME = account_data["username"]
        IG_PASSWORD = account_data["password"]

        async def save_auth_data(page: Page):
            storage = await page.context.storage_state()
            auth_data = json.dumps(storage, indent=4)
            await save_new_auth(auth_data, account_data["id"])

            # with open(AUTH_FILE, "w") as f:
            #     json.dump(storage, f)
            print("Authentication data saved")

        async def is_login_form_present(page: Page) -> bool:
            """Check if any login form elements are present"""
            selectors = [
                'input[name="username"]',
                'input[name="password"]',
                'button[type="submit"]'
            ]
            for selector in selectors:
                if await page.query_selector(selector):
                    return True
            return False

        async def validate_login_success(page: Page) -> bool:
            """Verify successful login by absence of login form and home page URL"""
            try:
                # Verify login form elements are gone
                if await is_login_form_present(page):
                    return False
                    
                # TODO: maybe Additional check for logout button presence
                return True
                
            except Exception as e:
                print(f"Validation error: {str(e)}")
                return False

        async def login_with_credentials(page: Page) -> bool:
            print("Attempting log in with credentials...")
            await page.goto(INSTAGRAM_AUTH_URL)
            
            # Handle cookie dialog
            try:
                await page.wait_for_selector('button:has-text("Allow essential and optional cookies")', timeout=5000)
                await page.click('button:has-text("Allow essential and optional cookies")')
                await page.wait_for_load_state("networkidle")
            except Exception:
                pass

            # Fill login form
            try:
                await page.wait_for_selector('input[name="username"]', timeout=10000)
                await page.fill('input[name="username"]', IG_USERNAME)
                await page.fill('input[name="password"]', IG_PASSWORD)
                await page.click('button[type="submit"]')
            except Exception as e:
                print(f"Form filling failed: {str(e)}")
                return False

            # Wait for either successful login or error
            try:
                async with asyncio.timeout(20):
                    while True:
                        if await validate_login_success(page):
                            return True
                        # if await page.query_selector('#slfErrorAlert'):
                        #     print("Login error detected")
                        #     return False
                        await asyncio.sleep(1)
            except TimeoutError:
                print("Login timeout")
                return False

        try:
            # Try to reuse existing auth
            if account_data.get("auth", False):
                print("Found existing auth file, trying to reuse...")
                
                storage_state = json.loads(account_data["auth"])
                # with open(AUTH_FILE) as f:
                #     storage_state = json.load(f)

                await self.page.context.add_cookies(storage_state["cookies"])
                
                await self.page.goto(INSTAGRAM_HOME_URL)
                if not await is_login_form_present(self.page):
                    print("Existing session appears valid")
                    return True
                
                print("Session expired or invalid")
                # AUTH_FILE.unlink()

            # Perform fresh login
            if not await login_with_credentials(self.page):
                raise Exception("Login flow failed")

            # Handle post-login modals
            try:
                await self.page.wait_for_selector('div[role="dialog"] button:has-text("Not Now")', timeout=5000)
                await self.page.click('div[role="dialog"] button:has-text("Not Now")')
            except Exception:
                pass

            await save_auth_data(self.page)
            return True

        except Exception as e:
            print(f"Login failed: {str(e)}")
            return False
    
# ----------- search --------------
# go throught each post/reel on the search page and find relevant content
    async def go_through_search_page(self, time_to_watch_1: int = 15, timer_to_stop: int = 10*60):
        """Go through the search page and like relevant posts"""

        for hashtag in self.hashtags:
            SEARCH_URL = "https://www.instagram.com/explore/search/keyword/?q="+ hashtag.replace("#", "%23")
            await self.page.goto(SEARCH_URL)

            await self.page.wait_for_timeout(2000)  # Wait for the page to load
            await self.page.wait_for_selector('a[href*="/p/"]')  # Wait for the posts to load

            # get ready to start watching
            a_tag: Locator = self.page.locator('a[href*="/p/"]')  # Select the first matching <a> tag
            a_tag = a_tag.first  # Get the first matching <a> tag
            if await a_tag.is_visible():
                await a_tag.click() 
                print("clicked the first post")
            
            time_to_watch_ms = time_to_watch_1*1000
            start_time = time.time()
            # watch till the given timer
            while time.time() - start_time < timer_to_stop:

                await self.page.wait_for_timeout(time_to_watch_ms)  # Wait for the page to load

                username_a_tag: Locator = self.page.locator('header[class="_aaqw"] a[role="link"] ')  # Select the first matching <a> tag
                username_a_tag = username_a_tag.first  # Get the first matching <a> tag

                # Extract link and username
                profile_link = await username_a_tag.get_attribute("href")
                if profile_link:
                    username = profile_link.strip("/").split("/")[-1]
                    print(username)
                    self.usernames.add(username)
                    await add_profile(self.id, username)  # Add to the database

                # like the post
                # await self.click_like_button(page_type="profile_reels")
                await self.page.keyboard.press('ArrowRight')

                # Wait for the page to load
                await self.page.wait_for_timeout(2000)
            

# ----------- reels ---------------
# watching reels based on the current algorithm, manipulate based on the topics [list of txt] in caption 
    async def reels_scroller(self, reels_data, watch_time = 2*60*60, max_usernames_count = 50):
        # Code to scroll through Instagram reels
        
        start_time = time.time()
        seen_count = 1
        while time.time() - start_time < watch_time:
            try:
                # process reel info
                reel_code = self.page.url.split('/')[-1] if self.page.url.split('/')[-1] != "" else self.page.url.split('/')[-2]
                print(f"{seen_count}. code = {reel_code} |", end=" ")
                try:
                    media_data = reels_data[reel_code]
                    caption: str = media_data["caption"]["text"]

                    self.reels_seen += 1
                    reel_on_topic = False

                    for topic in self.topics_list:
                        if topic.lower() in caption.lower():
                            reel_on_topic = True
                            break
                    
                    if not reel_on_topic:
                        print("skipping")
                        await self.page.wait_for_timeout(2*1000) # some delay to not be too fast in skipping
                        pass
                    else:
                        self.relevant_reels_seen += 1
                        await save_scraped_content(self.id, media_data) # save the scraped content to the database
                        await self.page.wait_for_timeout(10*1000)   # Watch for 10 secs       
                        # res = await click_icon(page, "Like")
                        await self.click_like_button(page_type="reels")

                        profile_username = media_data["owner"]["username"]
                        self.usernames.add(profile_username)

                        await add_profile(self.id, profile_username) # add to the database
                        # self.add_username_to_potential_list(profile_username)

                        await self.page.wait_for_timeout(20*1000)  # Watch for 20 more secs
                        print("taken")
                except Exception as e:
                    print(f"Error: {e}")
                    print("reel not in data going to next")


                await self.page.keyboard.press('ArrowDown')
                await self.page.wait_for_timeout(2*1000) # some breathing space for the url and stuff to update 
                seen_count+=1

            except Exception() as e:
                print(f"Error while scrolling: {e}")
            
            # stop if we have enough usernames
            if len(self.usernames) > max_usernames_count: 
                return

# start reels_scroller and store reels info
    async def watch_reels(self):
        # Create a shared data object to store network responses
        reels_data = {}

        # Setup network listener
        self.page.on("response", lambda response: self.handle_reels_network(response, reels_data))

        INSTAGRAM_REELS_URL = "https://www.instagram.com/reels"
        await self.page.goto(INSTAGRAM_REELS_URL)

        try:
            while len(reels_data.keys()) == 0:
                await asyncio.sleep(1)

            await self.reels_scroller(reels_data)
        except:
            input("stopped reels scrolling (waiting for a key to exit)")

    async def profiles_reels_watcher(self, profiles, timer_to_stop: int = 15*60):
        """Watch reels from a specific profile"""
        print("----PROFILE REELS WATCHER----")
        reels_data = dict()
        self.page.on("response", lambda response: self.handle_profile_reel_watcher_network(response, reels_data))
        seen_count = 1

        self.bio_data = dict()

        for username in profiles:
            print("watching profile reels for:", username)
            try:
                # go to the profile page
                PROFILE_URL = f"https://www.instagram.com/{username}/reels"
                await self.page.goto(PROFILE_URL)
                await self.page.wait_for_timeout(3*1000) # wait 3 secs for page to load

                # wait for the profile data to be saved
                start_time = time.time()
                while (not self.bio_data.get(username, False)) or (time.time()-start_time > 24) : # max wait for 24 secs (in case profile doesn't exist anymore / its private)
                    await self.page.wait_for_timeout(1000) # wait 1 sec before rechecking
                print("saved bio data")

                # wait for reels_data to be loaded
                while len(reels_data.keys()) == 0:
                    await asyncio.sleep(1)
                # print("got data for reels: ", list(reels_data.keys()))

                await self.page.wait_for_selector('a[href*="/reel/"]', timeout=30*1000)  # Wait for the reels to load
                # get ready to start watching
                a_tag : Locator = self.page.locator(f'a[href*="/reel/"]')  # Select the first matching <a> tag
                a_tag = a_tag.first  # Get the first matching <a> tag
                if await a_tag.is_visible():
                    await a_tag.click() 
                    print("clicked the first reel")
            
                start_time = time.time()
                # watch till the given timer
                while time.time() - start_time < timer_to_stop:

                    reel_code = self.page.url.split('/')[-1] if self.page.url.split('/')[-1] != "" else self.page.url.split('/')[-2]
                    print(f"{seen_count}. code = {reel_code} |", end=" ")
                    try:
                        media_data = reels_data[reel_code]
                        # print(media_data)

                        # wait for caption to be there in the data
                        if media_data.get("caption", False):
                            caption: str = media_data["caption"]["text"]
                        else:
                            while not media_data.get("caption", False):
                                await asyncio.sleep(1)
                            caption:str = media_data["caption"]

                        self.reels_seen += 1
                        reel_on_topic = False

                        for topic in self.topics_list:
                            if topic.lower() in caption.lower():
                                reel_on_topic = True
                                break
                        
                        if not reel_on_topic:
                            print("skipping")
                            await self.page.wait_for_timeout(2*1000) # some delay to not be too fast in skipping
                            pass
                        else:
                            self.relevant_reels_seen += 1
                            await save_scraped_content(self.id, media_data) # save the scraped content to the database
                            await self.page.wait_for_timeout(10*1000)   # Watch for 10 secs       
                            # like reel
                            await self.click_like_button(page_type="profile_reels")

                            await self.page.wait_for_timeout(20*1000)  # Watch for 20 more secs
                            print("taken")
                    except Exception as e:
                        print(f"Error: {e}")
                        print("reel not in data going to next")
                        await self.page.wait_for_timeout(2*1000) # some delay to not be too fast


                    seen_count+=1
                    await self.page.keyboard.press('ArrowRight')

            except Exception as e:
                print(f"Error watching profile reels / user has no reels posted")
                continue

            finally:
                await self.update_scraper("profile_reels", data={
                    "reels_seen": self.reels_seen,
                    "relevant_reels_seen": self.relevant_reels_seen,
                    "state": "profile_bio"
                })

# ---------- profiles --------------
# extract links and text from profile bios
    async def extract_links_from_bios(self):
        """Extract links from the bios of the saved usernames"""

        unique_usernames = list(self.usernames)
        
        self.bio_data = dict()

        self.page.on("response", lambda response: self.handle_profile_network(response))

        for username in unique_usernames:
            PROFILE_URL = f"https://www.instagram.com/{username}"
            await self.page.goto(PROFILE_URL)
            await self.page.wait_for_timeout(3*1000) # wait 3 secs for page to load
            start_time = time.time()
            while (not self.bio_data.get(username, False)) or (time.time()-start_time > 24) : # max wait for 24 secs (in case profile doesn't exist anymore / its private)
                await self.page.wait_for_timeout(1000) # wait 1 sec before rechecking

            await self.page.wait_for_timeout(3*1000) # avoid sudden shifts to different profiles (min 6 secs on a profile)

        save_profile_data(self.bio_data)

# ------- network handlers ---------
# network handlers
    async def handle_profile_reel_watcher_network(self, response, reels_data: dict):
        url = response.url
        target_url = "https://www.instagram.com/graphql/query"

        if target_url in url:
            try:
                response_data = await response.json()

                #reels data
                if response_data["data"].get("xdt_api__v1__clips__user__connection_v2", False):
                    new_reels_data = {}
                    for edge in response_data["data"]["xdt_api__v1__clips__user__connection_v2"]["edges"]:
                        media = edge["node"]["media"]
                        new_reels_data[ media["code"] ] = media

                    reels_data.update(new_reels_data)

                # user info response
                if response_data["data"].get("user", False):
                    # it is confirmed that this is a user profile data
                    new_bio_data = dict()
                    username = response_data["data"]["user"]["username"]
                    bio_txt = response_data["data"]["user"]["biography"]
                    bio_links = []

                    for link_obj in response_data["data"]["user"]["bio_links"]: 
                        bio_links.append( link_obj["url"] )
                    
                    new_bio_data[username] = {"username": username, "links": bio_links, "text": bio_txt}

                    self.bio_data.update(new_bio_data)
                    await update_profile(self.id, username, new_bio_data[username])

            except Exception as e:
                print(f"Failed to process response from {url}: {str(e)}")
    
        if "comments" in url:
            response_data = await response.json()
            text = response_data["caption"]["text"]
            media_id = response_data["caption"]["media_id"]

            for reel in reels_data.values():
                if media_id == reel["pk"]:
                    reel["caption"] = text

    async def handle_profile_network(self, response):
        url = response.url
        target_url = "https://www.instagram.com/graphql/query"

        if target_url in url:
            try:
                response_data = await response.json()

                if response_data["data"].get("user", False):
                    # it is confirmed that this is a user profile data
                    new_bio_data = dict()
                    username = response_data["data"]["user"]["username"]
                    bio_txt = response_data["data"]["user"]["biography"]
                    bio_links = []

                    for link_obj in response_data["data"]["user"]["bio_links"]: 
                        bio_links.append( link_obj["url"] )
                    
                    new_bio_data[username] = {"username": username, "links": bio_links, "text": bio_txt}

                    self.bio_data.update(new_bio_data)
                    await update_profile(self.id, username, new_bio_data[username])

            except Exception as e:
                print(f"Failed to process response from {url}: {str(e)}")

    async def handle_reels_network(self, response, reels_data: dict):
        """Process network responses and store reels data"""
        url = response.url
        
        target_url = "https://www.instagram.com/graphql/query"

        # Check if this is the URL we're interested in
        if target_url in url:
            try:
                response_data = await response.json()
        
                if response_data["data"].get("xdt_api__v1__clips__home__connection_v2", False) :
                    print(f"Found new reels update request")

                    new_reels_data = {}
                    for edge in response_data["data"]["xdt_api__v1__clips__home__connection_v2"]["edges"]:
                        media = edge["node"]["media"]
                        new_reels_data[ media["code"] ] = media

                    reels_data.update(new_reels_data)
                    # await save_many_scraped_content(self.id, list(new_reels_data.values()))

                    # Save to all reels content as json
                    # import os
                    # os.makedirs("network", exist_ok=True)
                    # with open(f"network/reels_feed_data.json", 'w') as f:
                    #     json.dump(reels_data , f)
            except Exception as e:
                print(f"Failed to process response from {url}: {str(e)}")

# utils to save and click stuff
    def add_username_to_potential_list(self, username):
        try:
            with open("profiles_list.txt", "a") as f:
                f.write(username+"\n")
            return True
        except:
            return False

    async def click_icon(self, type):
        """Click on an SVG icon by its aria-label"""
        try:
            script = '''
                    (type) => {
                        let svg = document.querySelector(`svg[aria-label="${type}"]`);   
                        let button = svg.closest(`div[role="button"]`)
                        button.click()
                    }
                    '''
            await self.page.evaluate(script, type)
            await self.page.wait_for_timeout(1500)  # Wait for the action to complete
            return True
        except Exception as e:
            print(f"Error clicking SVG button with aria-label='{type}': {e}")
            return False

    async def click_like_button(self, page_type: str):
        if page_type== "reels":
            # like using the mouse click
    
            x = 929+12 # x coordinate for like button
            y = 366+12 # y coordinate for like button
            await self.page.mouse.move(x, y)
            await self.page.wait_for_timeout(300)  # Pause for visibility
            await self.page.mouse.click(x, y, button="left")
        
        elif page_type== "profile_reels":
            # like using the SVG icon selector
            await self.click_icon("Like")

    async def update_scraper(self, state, data=None):
        self.state = state
        new_time = time.time() - self.start_time

        if data != None:
            data["total_time"] = self.total_time + new_time
            await update_scraper_data(self.id, data=data)
        else:
            await update_scraper_data(self.id, 
                data=dict({
                    "state": state,
                    "total_time": self.total_time + new_time
                })
            )
        
        self.start_time = time.time()

# main loop runner (switching between watching reels and extracting links)
    async def loop_runner(self):
        ''' run reel watcher and bio link extractor in a loop '''
    
        self.start_time = time.time()

        try:

            # Sign-IN
            await self.signIn()

            if self.state == "new": 
                await self.update_scraper("search")
            
            if self.state == "search":
                await self.go_through_search_page()
                await self.update_scraper("profile_reels")
                
            if self.state == "profile_reels":
                unscraped_profiles = await get_unscraped_profiles(self.id)
                await self.profiles_reels_watcher(profiles=unscraped_profiles)

                await self.update_scraper("reels", data={
                    "reels_seen": self.reels_seen,
                    "relevant_reels_seen": self.relevant_reels_seen,
                    "state": "reels"
                })

            # await page.wait_for_timeout(30*60*1000)
            start_time = time.time()

            while time.time()-start_time < self.loop_watch_time:

                if self.state == "reels":
                    # WATCH REELS
                    await self.watch_reels()

                    await self.update_scraper("profile_bio", data={
                        "reels_seen": self.reels_seen,
                        "relevant_reels_seen": self.relevant_reels_seen,
                        "state": "profile_bio"
                    })

                unscraped_profiles = await get_unscraped_profiles(self.id)
                self.usernames.update(unscraped_profiles)

                if self.state == "profile_bio":
                    # EXTRACT LINKS FROM PROFILES
                    await self.extract_links_from_bios()

                    await self.update_scraper("reels")

                self.usernames.clear()

        except Exception as e:
            print("error occurred from in insta automator")
        except KeyboardInterrupt:
            print("keyboard Interrupt")
        except asyncio.CancelledError:
            # Perform cleanup (close browsers, files, etc.)
            new_time = time.time() - start_time
            await update_scraper_data(self.id, 
                data=dict({
                    "reels_seen": self.reels_seen,
                    "relevant_reels_seen": self.relevant_reels_seen,
                    "state": "profile_bio",
                    "total_time": self.total_time + new_time
                })
            )
            raise
        finally:
            new_time = time.time() - start_time
            await update_scraper_data(self.id, 
                data=dict({
                    "reels_seen": self.reels_seen,
                    "relevant_reels_seen": self.relevant_reels_seen,
                    "state": "profile_bio",
                    "total_time": self.total_time + new_time
                })
            )
