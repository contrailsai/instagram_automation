import asyncio
import json
import os
from pathlib import Path
from playwright.async_api import Page, Browser, Response
from typing import Optional

async def signIn(page: Page, browser: Browser) -> bool:
    AUTH_FILE = Path("ig_auth.json")
    INSTAGRAM_AUTH_URL = "https://www.instagram.com/accounts/login/"
    INSTAGRAM_HOME_URL = "https://www.instagram.com/"
    IG_USERNAME = os.getenv("IG_USERNAME")
    IG_PASSWORD = os.getenv("IG_PASSWORD")

    async def save_auth_data(context):
        storage = await context.storage_state()
        with open(AUTH_FILE, "w") as f:
            json.dump(storage, f)
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
            # Wait for potential navigation to complete
            # await page.wait_for_url(INSTAGRAM_HOME_URL, timeout=15000)
            
            # Verify login form elements are gone
            if await is_login_form_present(page):
                return False
                
            # Additional check for logout button presence
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
                    if await page.query_selector('#slfErrorAlert'):
                        print("Login error detected")
                        return False
                    await asyncio.sleep(1)
        except TimeoutError:
            print("Login timeout")
            return False

    try:
        # Try to reuse existing auth
        if AUTH_FILE.exists():
            print("Found existing auth file, trying to reuse...")
            with open(AUTH_FILE) as f:
                storage_state = json.load(f)
            await page.context.add_cookies(storage_state["cookies"])
            
            await page.goto(INSTAGRAM_HOME_URL)
            if not await is_login_form_present(page):
                print("Existing session appears valid")
                return True
            
            print("Session expired or invalid")
            AUTH_FILE.unlink()

        # Perform fresh login
        if not await login_with_credentials(page):
            raise Exception("Login flow failed")

        # Handle post-login modals
        try:
            await page.wait_for_selector('div[role="dialog"] button:has-text("Not Now")', timeout=5000)
            await page.click('div[role="dialog"] button:has-text("Not Now")')
        except Exception:
            pass

        await save_auth_data(page)
        return True

    except Exception as e:
        print(f"Login failed: {str(e)}")
        return False
