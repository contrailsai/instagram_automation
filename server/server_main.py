# server_main.py
from fastapi import FastAPI, HTTPException
import os
import json
import uvicorn
from dotenv import load_dotenv
from pydantic import BaseModel
import asyncio
from multiprocessing import Process
# import multiprocessing
from google import generativeai as genai
import base64
from llm_instructions import title_keywords_hashtags_instruction

from server.database.scrapers import get_scraper_name, get_scraper_name, new_scraper, scraper_check_suspended, get_scraper_state, get_all_scrapers, get_all_scraper_ids, get_scraper_data_by_id, update_activity
from server.database.accounts import get_all_accounts, insert_account, get_unassigned_account, assign_scraper_to_account
from server.database.profiles import get_profiles_data, get_profile_data
from server.database.links import get_links_data, get_all_links_data, get_link_data, update_link_state
from server.database.content import get_reels_data
from server.database.ads import get_ads_data
from server.database.targeted_apps import get_targeted_app, get_targeted_apps, insert_targeted_app

from fastapi.middleware.cors import CORSMiddleware
import psutil 
import tempfile
import pickle

load_dotenv()

class Prompt(BaseModel):
    text: str

class AccountModel(BaseModel):
    username: str
    password: str

app = FastAPI()

# Use a file to store process information between reloads
PROCESS_TRACKING_FILE = os.path.join(tempfile.gettempdir(), "scraper_processes.pkl")
def save_process_info(processes_dict: dict[str, int]):
    """Save process info to a file"""
    with open(PROCESS_TRACKING_FILE, "wb") as f:
        pickle.dump(processes_dict, f)

def load_process_info() -> dict[str, int]:
    """Load process info from file"""
    if os.path.exists(PROCESS_TRACKING_FILE):
        try:
            with open(PROCESS_TRACKING_FILE, "rb") as f:
                return pickle.load(f)
        except:
            return {}
    return {}

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow only localhost:3000
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

running_processes: dict[str, int] = load_process_info()

llm_api_key = os.getenv("GENAI_API_KEY")

genai.configure(api_key=llm_api_key)
llm_model = genai.GenerativeModel(model_name='gemini-1.5-flash')

@app.get("/")
async def read_root():
    return {"message": "instagram automated scraper API"}

# ------- SCRAPER ENDPOINTS --------
@app.get("/all_scrapers")
async def all_scrapers():
    '''Get all scrapers from the database'''
    try:
        all_scrapers = await get_all_scrapers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch scrapers: {str(e)}")
    
    return {
        "status": "success",
        "scrapers": all_scrapers
    }

@app.get("/scraper_data/{scraper_id}")
async def scraper_data(scraper_id: str):
    '''Get a specific scraper from the database'''
    try:
        scraper = await get_scraper_data_by_id(scraper_id)
        # print(scraper)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch scraper: {str(e)}")
    
    return {
        "status": "success",
        "scraper": scraper
    }

# -------- INSERT TARGETED APPS -----------

class insertapp(BaseModel):
    scraper_id: str
    app_name: str
    keywords: list[str]


@app.post("/insert-targeted-app")
async def insert_targeted_app_data(doc : insertapp):
    '''Insert a targeted app into the database'''
    try:
        await insert_targeted_app(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to insert targeted app: {str(e)}")
    
    return {
        "status": "success",
        "message": "Targeted app inserted successfully"
    }

@app.get("/get-targeted-app/{app_id}")
async def get_targeted_app_data(app_id: str):
    '''get targeted app info'''
    try:
        doc = await get_targeted_app(app_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to insert targeted app: {str(e)}")
    
    return {
        "status": "success",
        "app": doc
    }

@app.get("/get-targeted-apps/{scraper_id}")
async def get_targeted_apps_data(scraper_id: str):
    '''get targeted app info'''
    try:
        doc = await get_targeted_apps(scraper_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to insert targeted app: {str(e)}")
    
    return {
        "status": "success",
        "app": doc
    }


@app.get("/reels_data/{scraper_id}")
async def reels_scraper(scraper_id: str):
    '''Get a specific scraper from the database'''
    try:
        reels = await get_reels_data(scraper_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch scraper: {str(e)}")
    
    return {
        "status": "success",
        "reels": reels
    }

@app.get("/profiles_data/{scraper_id}")
async def profiles_scraper(scraper_id: str):
    '''Get a specific scraper from the database'''
    try:
        profiles = await get_profiles_data(scraper_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch scraper: {str(e)}")
    
    return {
        "status": "success",
        "profiles": profiles
    }

# --------------ADS----------------

@app.get("/ads_data/{scraper_id}")
async def ads_scraper(scraper_id: str):
    '''Get a specific scraper from the database'''
    try:
        ads = await get_ads_data(scraper_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch scraper: {str(e)}")
    
    return {
        "status": "success",
        "ads": ads
    }

# -------------------------------
@app.get("/links/{scraper_id}")
async def links_scraper(scraper_id: str):
    '''Get a specific scraper from the database'''
    try:
        links = await get_links_data(scraper_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch scraper: {str(e)}")
    
    return {
        "status": "success",
        "links": links
    }

@app.get("/links/")
async def links_scraper():
    '''Get a specific scraper from the database'''
    try:
        links = await get_all_links_data()
        scrapers_data = await get_all_scrapers()
        
        scraper_name = dict()
        for scraper in scrapers_data:
            scraper_name[ scraper["id"] ] = scraper["title"]
        
        formated_links =[] 

        for link in links:
            formated_links.append({
                "link_id": link["id"],
                "link": link["link"],
                "profiles": link["profiles"],
                "suspicious": link["suspicious"],
                "campaign_id": link["scraper_id"],
                "campaign_name": scraper_name.get(link["scraper_id"], ""),
                "manual_check_result": link["manual_check_result"],
                "state": link["state"],
            })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch scraper: {str(e)}")
    
    return {
        "status": "success",
        "links": formated_links
    }

@app.get("/data-of-link/{link_id}")
async def data_of_link(link_id: str):
    try:
        link = await get_link_data(link_id)
        scraper_name = await get_scraper_name(link["scraper_id"])

        profiles_data = dict()
        for profile in link["profiles"]:
            profiles_data[profile] = await get_profile_data(profile)

        formated_link = {
            "link_id": link_id,
            "link": link["link"],
            "profiles": profiles_data,
            "suspicious": link["suspicious"],
            "campaign_id": link["scraper_id"],
            "campaign_name": scraper_name,
            "manual_check_result": link["manual_check_result"],
            "state": link["state"],
            "preview_image": link["screenshot"],
        }

        if link.get("review_notes", False):
            formated_link["review_notes"] = link["review_notes"]

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch scraper: {str(e)}")
    
    return {
        "status": "success",
        "link": formated_link
    }

class StatusUpdate(BaseModel):
    status: str
    notes: str
    
@app.post("/links/{link_id}/status")
async def update_link_status(link_id: str, update_data: StatusUpdate):
    '''Update the status of a link'''
    try:
        await update_link_state(link_id, {
            "manual_check_result": update_data.status, 
            "review_notes": update_data.notes
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update link status: {str(e)}")
    
    return {
        "status": "success",
        "message": "Link status updated successfully"
    }


@app.get("/suspend_scraper/{scraper_id}")
async def suspend_scraper(scraper_id: str):
    '''Suspend a scraper'''
    try:
        await stop_scraper(scraper_id)
        await update_activity(scraper_id, False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to suspend scraper: {str(e)}")
    
    return {
        "status": "success",
        "message": "Scraper suspended successfully"
    }

@app.get("/start_scraper/{scraper_id}")
async def start_requested_scraper(scraper_id: str):
    '''Start a scraper'''
    try:
        is_suspended: bool = await scraper_check_suspended(scraper_id)
        if is_suspended:
            return {
                "status": "failure", 
                "message": "scraper was suspended",
            }
        # Load the latest process info
        global running_processes
        running_processes = load_process_info()
        
        # Start the scraper if it's not already running
        if scraper_id not in running_processes or not psutil.pid_exists(running_processes[scraper_id]):
            await start_scraper(scraper_id)
            await update_activity(scraper_id, True)
        else:
            print(f"Scraper {scraper_id} is already running with PID {running_processes[scraper_id]}")
            
        new_state = await get_scraper_state(scraper_id)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start scraper: {str(e)}")
    
    return {
        "status": "success",
        "message": "Scraper started successfully",
        "new_state": new_state
    }

# ------- ACCOUNT ENDPOINTS --------

@app.get("/all_accounts")
async def all_accounts():
    '''Get all accounts from the database'''
    try:
        all_accounts = await get_all_accounts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch accounts: {str(e)}")
    
    return {
        "status": "success",
        "accounts": all_accounts
    }

@app.get("/idle_account")
async def get_idle_account():
    '''Get an idle account from the database'''
    try:
        idle_account = await get_unassigned_account()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch idle account: {str(e)}")
    
    return {
        "status": "success",
        "account_available": True if idle_account!= None else False,
    }

@app.post("/create_account")
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

# ---------GENERATE SCRAPER, START SCRAPERS ------------
@app.post("/generate_scraper")
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
        "id": document['id']
    }

def scraper_runner(scraper_id):
    import asyncio
    from reels_scroller.main import main as automation_controller
    asyncio.run(automation_controller(scraper_id))

async def start_scraper(scraper_id):
    is_suspended: bool = await scraper_check_suspended(scraper_id)
    if is_suspended:
        return False
    # Create the process
    bg_process = Process(target=scraper_runner, args=(scraper_id,))
    bg_process.start()
    
    # Store the PID, not the process object
    running_processes[scraper_id] = bg_process.pid
    save_process_info(running_processes)
    
    print(f"Started scraper {scraper_id} with PID {bg_process.pid}")
    print("Current running processes:", running_processes)
    
    return bg_process.pid

async def stop_scraper(scraper_id):
    # Reload the dictionary in case it's been updated
    global running_processes
    running_processes = load_process_info()
    
    print(f"Running stop scraper for {scraper_id}")
    print(running_processes)
    
    if scraper_id in running_processes:
        process_pid = running_processes[scraper_id]
        try:
            # Check if process exists and terminate it
            if psutil.pid_exists(process_pid):
                parent = psutil.Process(process_pid)
                
                # Terminate child processes first (if any)
                children = parent.children(recursive=True)
                for child in children:
                    child.terminate()
                
                # Terminate the main process
                parent.terminate()
                
                # Wait a bit and kill forcefully if needed
                gone, alive = psutil.wait_procs([parent], timeout=3)
                if alive:
                    for p in alive:
                        p.kill()
                
                print(f"Successfully stopped scraper {scraper_id} with PID {process_pid}")
            else:
                print(f"Process with PID {process_pid} does not exist anymore")
        except Exception as e:
            print(f"Error stopping scraper {scraper_id}: {e}")
        
        # Remove from dictionary and save
        del running_processes[scraper_id]
        save_process_info(running_processes)
        return True
    
    print(f"Scraper {scraper_id} not found in running processes")
    return False

async def stop_all_scrapers():
    # Reload the dictionary
    global running_processes
    running_processes = load_process_info()
    
    scraper_ids = list(running_processes.keys())
    for scraper_id in scraper_ids:
        await stop_scraper(scraper_id)

async def start_all_scrapers():
    # Start all scrapers here
    ids = await get_all_scraper_ids()
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