# server_main.py
from fastapi import FastAPI, HTTPException
import os
import json
import uvicorn
from dotenv import load_dotenv
from pydantic import BaseModel
import asyncio
import multiprocessing
from google import generativeai as genai
import base64
from llm_instructions import title_keywords_hashtags_instruction
from database import new_scraper, get_all_document_ids, insert_account, get_unassigned_account, assign_scraper_to_account

load_dotenv()

class Prompt(BaseModel):
    text: str

class AccountModel(BaseModel):
    username: str
    password: str

app = FastAPI()

llm_api_key = os.getenv("GENAI_API_KEY")

genai.configure(api_key=llm_api_key)
llm_model = genai.GenerativeModel(model_name='gemini-1.5-flash')

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Async FastAPI server!"}

@app.post("/save-account")
async def save_account(account: AccountModel):
    '''Save an Instagram user account to the database'''
    # Data is automatically extracted from JSON thanks to Pydantic
    username = account.username
    password = account.password

    # Encode username and password in base64
    encoded_username = base64.b64encode(username.encode("utf-8")).decode("utf-8")
    encoded_password = base64.b64encode(password.encode("utf-8")).decode("utf-8")

    # Save to database
    account_data = {
        "username": encoded_username,
        "password": encoded_password
    }
    
    try:
        await insert_account(account_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save account: {str(e)}")

    return {
        "status": "success",
        "message": "Account saved successfully"
    }

@app.post("/generate-new-agent")
async def generate_prompt(prompt: Prompt):

    # check if a account is availabel
    usable_account = await get_unassigned_account()
    if not usable_account:
        return {
            "status": "error",
            "message": "No available account found"
        }
    
    print("usable_account = ", usable_account)

    user_text = prompt.text
    response = await title_keywords_hashtags_instruction(llm_model, user_text)
    print(response)

    document = await new_scraper(
        text=user_text, 
        topic_attributes=response.get('keywords', []), 
        hashtags=response.get('hashtags', []),
        scraper_name= response.get('title', "") 
    )
    await assign_scraper_to_account(document['id'], usable_account['id'])
    await start_scraper( document['id'] )

    return {
        "status": "success",
        "message": "Scraper created successfully",
    }

def scraper_runner(scraper_id):
    import asyncio
    from reels_scroller.main import main as automation_controller
    asyncio.run(automation_controller(scraper_id))

async def start_scraper(scraper_id):
    bg_process = multiprocessing.Process(target=scraper_runner, args=(scraper_id,))
    bg_process.start()

async def start_all_scrapers():
    # Start all scrapers here
    ids = await get_all_document_ids()

    print("ids = ", ids)

    for scraper_id in ids:
        await start_scraper(scraper_id)

if __name__ == "__main__":

    asyncio.run(start_all_scrapers())

    # Start FastAPI server
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "server_main:app",
        host="0.0.0.0",
        port=port,
        reload=True,    
        workers=1  # Disable reload if you need multiple workers
    )