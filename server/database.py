# database.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from dotenv import load_dotenv
import base64
from bson.objectid import ObjectId

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

# SCRAPERS DATABASE FUNCTIONS

async def new_scraper(text: str, topic_attributes, hashtags, scraper_name) -> dict:
    # select the correct collection
    collection = db["scrapers"]

    document = {
        "text": text,
        "topic_attributes": topic_attributes,
        "hashtags": hashtags,
        "scraper_name": scraper_name
    }
    result = await collection.insert_one(document)
    return {"id": str(result.inserted_id), **document}

async def get_all_document_ids() -> list:
    # select the correct collection
    collection = db["scrapers"]
    
    documents = await collection.find({}, {"_id": 1}).to_list(length=None)
    return [str(doc["_id"]) for doc in documents]

async def get_all_documents() -> list:
    # select the correct collection
    collection = db["scrapers"]
    
    documents = await collection.find().to_list(length=None)
    return [{"id": str(doc["_id"]), **doc} for doc in documents]

async def get_document_by_id(document_id: str) -> dict:
    collection = db["scrapers"]
    try:
        object_id = ObjectId(document_id)
    except: # invalid id format
        return None
    
    document = await collection.find_one({"_id": object_id})
    if document:
        return {"id": str(document["_id"]), **document}
    return None

def updated_doc_properties(doc: dict) -> dict:
    update_doc = dict({})

    if doc.get("reels_seen", False):
        update_doc["reels_seen"] = doc["reels_seen"]

    if doc.get("relevant_reels_seen", False):
        update_doc["relevant_reels_seen"] = doc["relevant_reels_seen"]

    if doc.get("state", False):
        update_doc["state"] = doc["state"]

    return update_doc

async def update_scraper_data(scraper_id: str, data: dict) -> dict:
    # select the correct collection
    collection = db["scrapers"]
    
    try:
        scraper_object_id = ObjectId(scraper_id)
    except: # invalid id format
        return None

    update_doc = updated_doc_properties(data)

    result = await collection.update_one(
        {"_id": scraper_object_id},
        {"$set": update_doc},
        upsert=True
    )
    return {"id": str(result.upserted_id), **data}

# ACCOUNTS DATABASE FUNCTIONS

async def insert_account(account_data: dict) -> dict:
    # select the correct collection
    collection = db["accounts"]

    result = await collection.insert_one(account_data)
    return {"id": str(result.inserted_id), **account_data}

async def get_account_by_scraper_id(scraper_id: str) -> dict:
    # select the correct collection
    collection = db["accounts"]

    document = await collection.find_one({"scraper_id": scraper_id})
    document["username"] = base64.b64decode(document["username"]).decode("utf-8")
    document["password"] = base64.b64decode(document["password"]).decode("utf-8")

    if document:
        return {"id": str(document["_id"]), **document}
    return None

async def save_new_auth(auth_data: dict, account_id:str) -> dict:
    # select the correct collection
    collection = db["accounts"]
    
    try:
        account_object_id = ObjectId(account_id)
    except: # invalid id format
        return None

    result = await collection.update_one(
        {"_id": account_object_id},
        {
            "$set": {
                "auth": auth_data,
            }
        },
        upsert=True
    )
    return {"id": str(result.inserted_id), **auth_data}

async def get_unassigned_account() -> dict:
    # select the correct collection
    collection = db["accounts"]
    
    document = await collection.find_one({"scraper_id": None})
    if document:
        return {"id": str(document["_id"]), **document}
    return None

async def assign_scraper_to_account(scraper_id: str, account_id: str) -> None:
    # select the correct collection
    collection = db["accounts"]

    try:
        account_object_id = ObjectId(account_id)
    except: # invalid id format
        return None

    await collection.update_one(
        {"_id": account_object_id},
        {
            "$set": {
                "scraper_id": scraper_id,
            }
        }
    )


# SCRAPED PROFILES DATABASE FUNCTIONS

async def add_profile(scraper_id: str, username: str) -> dict:
    # select the correct collection
    collection = db["scrape_profiles"]

    double_check = await collection.find_one({"scraper_id": scraper_id, "username": username})
    if double_check:
        return {"id": str(double_check["_id"])}

    profile = dict()
    profile["scraper_id"] = scraper_id
    profile["saved_on"] = datetime.utcnow()
    profile["scraped"] = False
    profile["username"] = username

    result = await collection.insert_one(profile)
    return {"id": str(result.inserted_id)}

async def update_profile(scraper_id: str, username: str, data: dict) -> dict:
    # select the correct collection
    collection = db["scrape_profiles"]

    result = await collection.update_one(
        {"scraper_id": scraper_id, "username": username},
        {
            "$set": {
                "scraped": True,
                "bio": data["text"],
                "links": data["links"]
            }
        }
    )
    return {"id": str(result.upserted_id), **data}

async def get_unscraped_profiles(scraper_id: str) -> list:
    # select the correct collection
    collection = db["scrape_profiles"]

    documents = await collection.find({"scraper_id": scraper_id, "scraped": False}, {"username": 1, "_id": 0}).to_list(length=None)
    return [doc["username"] for doc in documents]

# SCRAPED CONTENT DATABASE FUNCTIONS

def create_doc(media):
    try:
        doc = {
            "code": media.get("code", ""),
            "like_count": media.get("like_count", 0),
            "comment_count": media.get("comment_count", 0),
            "view_count": media.get("view_count", 0),
            "taken_at": media.get("taken_at", None),
            "location": media.get("location", None)
        }
        
        # Safely get caption text
        caption = media.get("caption", {})
        doc["caption"] = caption.get("text", "") if isinstance(caption, dict) else ""
        
        # Safely get username
        user = media.get("user", {})
        doc["username"] = user.get("username", "") if isinstance(user, dict) else ""
                
        return doc
    except Exception as e:
        # Fallback in case of any error
        print(f"Error creating document: {str(e)}")
        return {
            "code": media.get("code", ""),
            "error": "Failed to process complete media data"
        }

async def save_scraped_content(scraper_id: str, content: dict) -> dict:
    # select the correct collection
    collection = db["scraped_content"]

    doc = create_doc(content)
    doc["scraper_id"] = scraper_id
    doc["saved_on"] = datetime.utcnow()

    result = await collection.insert_one(doc)
    return {"id": str(result.inserted_id)}

async def save_many_scraped_content(scraper_id: str, contents: list) -> None:
    # select the correct collection
    collection = db["scraped_content"]

    documents = []
    print(len(contents))
    for content in contents:
        doc = create_doc(content)
        doc["scraper_id"] = scraper_id
        doc["saved_on"] = datetime.utcnow()
        documents.append(doc)
    print(len(documents))        
    await collection.insert_many(documents)