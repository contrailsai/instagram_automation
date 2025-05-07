import os
import json 
from playwright.async_api import Page, Locator

def save_profile_data(bio_data):
    filepath = "profiles_links_n_text.json"
    usernames_bio = dict()

    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            usernames_bio = json.load(f)
        
    usernames_bio.update(bio_data)

    with open(filepath, 'w') as f:
        json.dump(usernames_bio, f)

async def click_icon(page: Page, type):
    try:
        script = '''
                (type) => {
                    let svg = document.querySelector(`svg[aria-label="${type}"]`);   
                    let button = svg.closest(`div[role="button"]`)
                    button.click()
                }
                '''
        await page.evaluate(script, type)
        await page.wait_for_timeout(1000)  # Wait for the action to complete
        return True
    except Exception as e:
        print(f"Error clicking SVG button with aria-label='{type}': {e}")
        return False

async def click_like_button(page: Page):
    x = 929+12
    y = 366+12
    await page.mouse.move(x, y)
    await page.wait_for_timeout(300)  # Pause for visibility
    await page.mouse.click(x, y, button="left")

def add_username_to_potential_list(username):
    try:
        with open("potential_profiles_list.txt", "a") as f:
            f.write(username+"\n")
        return True
    except:
        return False