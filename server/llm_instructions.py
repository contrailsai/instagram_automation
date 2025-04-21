from google.generativeai import GenerativeModel
import json

async def relevancy_check(llm_model: GenerativeModel, video_caption: str, text_prompt: str, keywords: list[str]) -> bool:
    instruction = f"""
    Analyze the given caption for a short video and respond with "yes" or "no" if it is relavant to the topic and keywords of the searched topic. 
    given :-
    Text prompt: {text_prompt}
    Keywords: {" ,".join(keywords)}
    Caption: {video_caption}

    Here Text prompt is the text by user on the topic he is looking for. 
    Keywords are the keywords relevant to the topic find through the processing.
    Caption is the caption of the video which is being checked for relevancy to the topic. 

    Do not include any introductory text, explanations, markdown formatting, or any other text outside of the 1 word "yes" or "no". 
    JUST GIVE ME THE 1 WORD RESPONSE STRING WITH NO QUOTES OR ANYTHING.
    """

    contents = [instruction] # Gemini API expects a list of contents

    try:
        response = await llm_model.generate_content_async(contents=contents)

        # It's crucial to parse the LLM's text response as JSON
        # Add error handling in case the response is not valid JSON
        try:
            # Accessing the generated text
            llm_output_text: str = response.text
            llm_output_text: str = llm_output_text.strip() # Remove leading/trailing whitespace

            if "yes" in llm_output_text.lower():
                return True
            else:
                return False
            
        except Exception as ve:
            print(f"Error: LLM response validation failed: {ve}\nResponse text:\n{response.text}")
            return {"error": f"LLM response validation failed: {ve}", "raw_response": response.text}

    except Exception as e:
        # Handle potential errors during the API call itself
        print(f"Error calling Generative AI API: {e}")
        return {"error": f"Failed to generate content: {e}"}
    
async def title_keywords_hashtags_instruction (llm_model: GenerativeModel ,user_text: str) -> str:

    instruction = f"""
    Analyze the following user request, which describes a topic for finding social media content:
    "{user_text}"

    Based on this request, generate:
    1. A concise and descriptive title for this search topic.
    2. A list of relevant keywords (without '#') suitable for searching on social media platforms or search engines.
    3. A list of relevant hashtags (including the '#' symbol) commonly used for this topic on social media.

    Your response MUST be a valid JSON object containing ONLY the following keys:
    - "title": A string (the concise title).
    - "keywords": A list of strings (the relevant keywords).
    - "hashtags": A list of strings (the relevant hashtags, each starting with '#').

    Do not include any introductory text, explanations, markdown formatting, or any other text outside of the JSON structure itself. 
    JUST GIVE ME THE JSON STRING WITH NO QUOTES OR ANYTHING.

    Example Input: "latest news about electric cars"
    Example Output:
    {{
      "title": "Latest Electric Car News",
      "keywords": ["electric vehicles", "EV updates", "new electric cars", "tesla news", "automotive tech"],
      "hashtags": ["#ElectricCars", "#EV", "#ElectricVehicle", "#Tesla", "#AutoNews", "#FutureOfMobility"]
    }}

    Now, generate the JSON output for the user's request: "{user_text}"

    """

    contents = [instruction] # Gemini API expects a list of contents

    try:
        response = await llm_model.generate_content_async(contents=contents)

        # It's crucial to parse the LLM's text response as JSON
        # Add error handling in case the response is not valid JSON
        try:
            # Accessing the generated text
            llm_output_text = response.text
            # Clean potential markdown code fences if the model adds them despite instructions
            if llm_output_text.startswith("```json"):
                llm_output_text = llm_output_text[7:]
            if llm_output_text.endswith("```"):
                 llm_output_text = llm_output_text[:-3]
            llm_output_text = llm_output_text.strip() # Remove leading/trailing whitespace

            # Parse the cleaned text as JSON
            result = json.loads(llm_output_text)

            # Basic validation (optional but recommended)
            if not all(k in result for k in ["title", "keywords", "hashtags"]):
                 raise ValueError("LLM response missing required keys.")
            if not isinstance(result["title"], str) or \
               not isinstance(result["keywords"], list) or \
               not isinstance(result["hashtags"], list):
                 raise ValueError("LLM response has incorrect data types for keys.")
        
            return result 
            
        except json.JSONDecodeError:
            print(f"Error: LLM response was not valid JSON.\nResponse text:\n{response.text}")
            return {"error": "Failed to parse LLM response as JSON", "raw_response": response.text}
        except ValueError as ve:
            print(f"Error: LLM response validation failed: {ve}\nResponse text:\n{response.text}")
            return {"error": f"LLM response validation failed: {ve}", "raw_response": response.text}
        except Exception as e: # Catch other potential errors during processing
             print(f"An unexpected error occurred during JSON processing: {e}\nResponse text:\n{response.text}")
             return {"error": "An unexpected error occurred processing the LLM response", "raw_response": response.text}

    except Exception as e:
        # Handle potential errors during the API call itself
        print(f"Error calling Generative AI API: {e}")
        return {"error": f"Failed to generate content: {e}"}
    