from playwright.async_api import Page, Locator
import asyncio
import time
import google.generativeai as genai
import os
import base64
import requests

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

def add_username_to_potential_list(username):
    try:
        with open("potential_profiles_list.txt", "a") as f:
            f.write(username+"\n")
        return True
    except:
        return False

async def reels_scroller(page: Page, reels_data, watch_time = 2*60*60):

    topic_texts = ["ipl", "rcb", "gt", "csk", "dc", "kkr", "rr", "pk", "lsg", "srh", "mi", "cricket"]

    start_time = time.time()
    seen_count = 1
    while time.time() - start_time < watch_time:
        try:
            # process reel info
            reel_code = page.url.split('/')[-1] if page.url.split('/')[-1] != "" else page.url.split('/')[-2]
            print(f"{seen_count}. code = {reel_code}")
            try:
                media_data = reels_data[reel_code]
                caption = media_data["caption"]["text"]

                reel_on_topic = False

                for topic in topic_texts:
                    if topic in caption:
                        reel_on_topic = True
                        break
                
                if not reel_on_topic:
                    print("skipping")
                    await page.wait_for_timeout(2*1000) # some delay to not be too fast in skipping
                    pass
                else:
                    await page.wait_for_timeout(10*1000)   # Watch for 10 secs       
                    res = await click_icon(page, "Like")
                    print("LIKED") if res==True else print("NOT LIKED")

                    profile_username = media_data["owner"]["username"]

                    add_username_to_potential_list(profile_username)

                    await page.wait_for_timeout(20*1000)  # Watch for 20 more secs
                    print("taken")
            except Exception as e:
                print(f"Error: {e}")
                print("reel not in data going to next")


            await page.keyboard.press('ArrowDown')
            await page.wait_for_timeout(2*1000) # some breathing space for the url and stuff to update 
            seen_count+=1

        except Exception() as e:
            print(f"Error while scrolling: {e}")

async def profile_reels_watcher(page: Page, profile: str, timer_to_stop: int = 2*60*60, time_to_watch_1: int = 2*60):
    """Watch reels from a specific profile"""
    
    PROFILE_URL = f"https://www.instagram.com/{profile}/reels"
    await page.goto(PROFILE_URL)

    await page.wait_for_timeout(2000)  # Wait for the page to load
    await page.wait_for_selector('a[href*="/reel/"]')  # Wait for the reels to load


    # get ready to start watching
    a_tag : Locator = page.locator(f'a[href*="/reel/"]')  # Select the first matching <a> tag
    a_tag = a_tag.first  # Get the first matching <a> tag
    if await a_tag.is_visible():
        await a_tag.click() 
        print("clicked the first post")
    
    time_to_watch_ms = time_to_watch_1*1000
    start_time = time.time()
    # watch till the given timer
    while time.time() - start_time < timer_to_stop:
        await page.wait_for_timeout(time_to_watch_ms)  # Wait for the page to load

        # like the reel
        await click_icon(page, "Like")
        print("reel clicked")
        await page.keyboard.press('ArrowRight')

# async def generate_huggingface_response(text: str, model_name: str = "google/gemma-7b-it") -> str:
#     """
#     Generates a response from a Hugging Face model using text and optional images.

#     Args:
#         text: The text prompt.
#         image_paths: A list of image file paths (optional).
#         model_name: The Hugging Face model identifier.

#     Returns:
#         The generated text response from the model, or None if an error occurs.
#     """

#     api_token = os.getenv("HUGGINGFACE_API_KEY") # Get API key from environment variables.
#     if not api_token:
#         print("Error: Hugging Face API key not found in environment variables.")
#         return None

#     api_url = f"https://api-inference.huggingface.co/models/{model_name}"
#     headers = {"Authorization": f"Bearer {api_token}"}

#     payload = {"inputs": text}

#     # if image_paths:
#     #   #Hugging face inference API's for multimodal models vary greatly.
#     #   #This code is for text only, and will require modification to work with multimodal models.
#     #   print("Warning: Image inputs are not currently supported in this text-only example.")

#     try:
#         response = requests.post(api_url, headers=headers, json=payload)
#         response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
#         result = response.json()

#         if isinstance(result, list) and len(result) > 0 and "generated_text" in result[0]:
#             return result[0]["generated_text"].strip()
#         elif isinstance(result, dict) and "generated_text" in result:
#             return result["generated_text"].strip()
#         elif isinstance(result, list) and len(result) > 0 and "summary_text" in result[0]:
#             return result[0]["summary_text"].strip()
#         elif isinstance(result, dict) and "summary_text" in result:
#             return result["summary_text"].strip()
#         elif isinstance(result, str):
#             return result.strip()
#         else:
#             print(f"Unexpected response format: {result}")
#             return None

#     except requests.exceptions.RequestException as e:
#         print(f"Hugging Face API request failed: {e}")
#         return None
#     except KeyError:
#         print("Error: Response does not contain 'generated_text' or 'summary_text'")
#         return None
#     except Exception as e:
#         print(f"An unexpected error occurred: {e}")
#         return None


# async def generate_gemini_response(text: str, image_paths: list[str] = None) -> str:
#     """
#     Generates a response from the Gemini API using text and optional images.

#     Args:
#         text: The text prompt.
#         image_paths: A list of image file paths (optional).

#     Returns:
#         The generated text response from Gemini, or None if an error occurs.
#     """
#     print("key = ", os.getenv("GOOGLE_API_KEY"))
#     genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
#     model = genai.GenerativeModel('gemini-pro-vision')  # or 'gemini-pro' for text-only

#     topic = "gambling"

#     contents = []

#     start_context = f"given a caption of a reel and possibly a thumbnail. tell me if the reel is anyhow related to the topic {topic}. give the response in one digit only between 10 and 1 describing the relation of the topic to caption and thumbnail. 10 being the most related and 1 being the least related."

#     contents.append(start_context)
#     # Add text to the content
#     contents.append(text)

#     # Add images if provided
#     if image_paths:
#         for image_path in image_paths:
#             try:
#                 with open(image_path, "rb") as image_file:
#                     image_data = image_file.read()
#                 contents.append({"mime_type": "image/jpeg", "data": base64.b64encode(image_data).decode("utf-8")}) # or image/png, etc.
#             except FileNotFoundError:
#                 print(f"Error: Image file not found: {image_path}")
#                 return None
#             except Exception as e:
#                 print(f"Error reading image: {e}")
#                 return None

#     try:
#         response = await model.generate_content_async(contents)
#         response.resolve() # Ensure the response is resolved.
#         return response.text.strip() # return the text response.
#     except Exception as e:
#         print(f"Gemini API error: {e}")
#         return None
