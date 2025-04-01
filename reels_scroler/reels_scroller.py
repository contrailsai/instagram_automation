from playwright.async_api import Page
import asyncio
import time
import google.generativeai as genai
import os
import base64
import requests

async def reels_scroller(page: Page, reels_data):
    seen_count = 0  
    while True:
        try:
            start_time = time.time()
            # process reel info
            reel_code = page.url.split('/')[-1] if page.url.split('/')[-1] != "" else page.url.split('/')[-2]
            print(f"code = {reel_code}")
            try:
                media_data = reels_data[reel_code]
                print(f"text = {media_data["caption"]["text"]}")

                # process the caption text, img, possibly video / ss of video then do stuff with it

                response_value = await generate_huggingface_response(media_data["caption"]["text"])

                print("response value = ", response_value)

                await asyncio.sleep(20 - (time.time()-start_time))
            except:
                print("reel not in data going to next")
            await page.keyboard.press('ArrowDown')
            await asyncio.sleep(2) # some breathing space for the url and stuff to update 
            print(f"-------Reels scrolled: {seen_count}---------")
        except Exception() as e:
            print(f"Error while scrolling: {e}")


async def generate_huggingface_response(text: str, model_name: str = "google/gemma-7b-it") -> str:
    """
    Generates a response from a Hugging Face model using text and optional images.

    Args:
        text: The text prompt.
        image_paths: A list of image file paths (optional).
        model_name: The Hugging Face model identifier.

    Returns:
        The generated text response from the model, or None if an error occurs.
    """

    api_token = os.getenv("HUGGINGFACE_API_KEY") # Get API key from environment variables.
    if not api_token:
        print("Error: Hugging Face API key not found in environment variables.")
        return None

    api_url = f"https://api-inference.huggingface.co/models/{model_name}"
    headers = {"Authorization": f"Bearer {api_token}"}

    payload = {"inputs": text}

    # if image_paths:
    #   #Hugging face inference API's for multimodal models vary greatly.
    #   #This code is for text only, and will require modification to work with multimodal models.
    #   print("Warning: Image inputs are not currently supported in this text-only example.")

    try:
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        result = response.json()

        if isinstance(result, list) and len(result) > 0 and "generated_text" in result[0]:
            return result[0]["generated_text"].strip()
        elif isinstance(result, dict) and "generated_text" in result:
            return result["generated_text"].strip()
        elif isinstance(result, list) and len(result) > 0 and "summary_text" in result[0]:
            return result[0]["summary_text"].strip()
        elif isinstance(result, dict) and "summary_text" in result:
            return result["summary_text"].strip()
        elif isinstance(result, str):
            return result.strip()
        else:
            print(f"Unexpected response format: {result}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Hugging Face API request failed: {e}")
        return None
    except KeyError:
        print("Error: Response does not contain 'generated_text' or 'summary_text'")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


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
