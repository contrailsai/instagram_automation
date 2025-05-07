
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from dotenv import load_dotenv
import base64
from bson.objectid import ObjectId
from links import get_links_data

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

# CREATE
async def new_scraper(text: str, topic_attributes, hashtags, scraper_name) -> dict:
    # select the correct collection
    collection = db["scrapers"]

    document = {
        "text": text,
        "topic_attributes": topic_attributes,
        "hashtags": hashtags,
        "scraper_name": scraper_name,
        "active": True,
        "state": "new",
        "is_suspended": False
    }
    result = await collection.insert_one(document)
    return {"id": str(result.inserted_id), **document}

# GET

async def get_all_scrapers() -> list:
    # select the correct collection
    collection = db["scrapers"]
    
    documents = await collection.find({}).to_list(length=None)
    return [ dict({
        "id": str(doc["_id"]),
        "title": doc["scraper_name"],
        "state": doc.get("state", "new"),
        "active": doc.get("active", False),
        "reels_seen": doc.get("reels_seen", 0),
        "relevant_reels_seen": doc.get("relevant_reels_seen", 0),
    }) for doc in documents]

async def get_all_scraper_ids() -> list[str]:
    collection = db["scrapers"]

    documents = await collection.find({}, {"_id": 1}).to_list(length=None)
    return [ str(doc["_id"]) for doc in documents]

# async def get_all_documents() -> list:
#     # select the correct collection
#     collection = db["scrapers"]
    
#     documents = await collection.find().to_list(length=None)
#     return [{"id": str(doc["_id"]), **doc} for doc in documents]

async def get_scraper_name(scraper_id)-> str:
    collection = db["scrapers"]
    try:
        scraper_object_id = ObjectId(scraper_id)
    except: # invalid id format
        return None
    result: dict = await collection.find_one(
        {"_id": scraper_object_id},
        {"scraper_name": 1}
    )
    return result.get("scraper_name", "")

async def get_scraper_data_by_id(document_id: str) -> dict:
    collection = db["scrapers"]
    # print(document_id)
    try:
        object_id = ObjectId(document_id)
    except: # invalid id format
        return None
    
    document = await collection.find_one({"_id": object_id}, {"_id": 0})

    links_data = await get_links_data(document_id)
    if links_data:
        document["links"] = links_data
    else:
        document["links"] = []

    if document:
        document["id"] = str(document_id)
        return document
    return None

async def get_scraper_state(document_id: str) -> str:
    # select the correct collection
    collection = db["scrapers"]

    try:
        object_id = ObjectId(document_id)
    except: # invalid id format
        return None
    
    document = await collection.find_one({"_id": object_id}, {"state": 1, "_id": 0})
    return document["state"]

async def scraper_check_suspended(scraper_id: str) -> bool :
    collection = db["scrapers"]
    
    try:
        scraper_object_id = ObjectId(scraper_id)
    except: # invalid id format
        return None

    result = await collection.find_one(
        {"_id": scraper_object_id},
        {"is_suspended": 1}
    )
    if result["is_suspended"]:
        return True
    return False


# UPDATE
async def set_scraper_activity(document_id: str, new_status: bool) -> dict:
    ''' set the status of the scraper false for suspending, true for running '''
    collection = db["scrapers"]
    try:
        object_id = ObjectId(document_id)
    except: # invalid id format
        return None
    
    document = await collection.find_one_and_update(
        {"_id": object_id},
        {"$set": {"active": new_status}},
        upsert=True
    )
    return True

def updated_doc_properties(doc: dict) -> dict:
    update_doc = dict({})

    if doc.get("reels_seen", False):
        update_doc["reels_seen"] = doc["reels_seen"]

    if doc.get("relevant_reels_seen", False):
        update_doc["relevant_reels_seen"] = doc["relevant_reels_seen"]

    if doc.get("state", False):
        update_doc["state"] = doc["state"]

    if doc.get("total_time", 0):
        update_doc["total_time"] = doc["total_time"]

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

async def update_activity(scraper_id: str, new_active_state: bool):
    collection = db["scrapers"]
    
    try:
        scraper_object_id = ObjectId(scraper_id)
    except: # invalid id format
        return None

    result = await collection.update_one(
        {"_id": scraper_object_id},
        {"$set": {"active": new_active_state }},
        upsert=True
    )
    return {"id": str(result.upserted_id)}


# frequency of keywords seen
# FREQUENCY, PRIORITY, of KEYWORDS BASED DATA

# {
#     "scraper_id": str,
#     "freq": {
#         "topic a": 5,
#         "topic b": 3,
#     },
#     "priority": {
#         "topic a": 1,
#         "topic b": 5,
#     }
# }

# CREATE
async def create_freq_stats(doc: dict):
    collection = db["keywords_stats"]
    
    result = await collection.insert_one(doc)
    return {"id": str(result.inserted_id)}

# GET
async def get_freq_stats(scraper_id: str):
    try:    
        collection = db["keywords_stats"]
        document = await collection.find_one(
            {"scraper_id": scraper_id},
            {"_id": 0}
        )
        return document
    except: 
        return None

# UPDATE
async def update_freq_stats(scraper_id: str, new_stats: dict):
    # select the correct collection
    collection = db["keywords_stats"]
    
    await collection.update_one(
        {"scraper_id": scraper_id},
        {"$set": {"freq": new_stats}},
        upsert=True
    )
    return

