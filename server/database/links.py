
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

# TYPICAL LINKS DATA
# {
#     "link": "https://....",
#     "profiles": ["username-1", "username2"],
#     "suspicious": "",
#     "state": "",
#     "manual_check_result": ""
#     "screenshot": ""
# }

# CREATE
async def save_links_data(data : dict, scraper_id: str):
    # select the correct collection
    collection = db["links"]

    documents = []
    # print(len(contents))
    for link in data.keys():

        doc = dict({
            "link": link,
            "profiles": data[link]["profiles"],
            "suspicious": data[link].get("suspicious", ""),
            "state": "",
            "manual_check_result": "",
            "scraper_id": scraper_id
        })

        documents.append(doc)
    # print(len(documents))        
    await collection.insert_many(documents)

# GET
async def get_links_data(scraper_id: str, screenshot: bool = False) -> dict:
    # select the correct collection
    collection = db["links"]
    links = set()
    documents: list[dict] = await collection.find({"scraper_id": scraper_id, }).to_list(length=None)
    
    final_result = []

    for doc in documents:
        # doc["id"] = str(doc["_id"])
        doc["_id"] = str(doc["_id"])
        if not screenshot:
            doc.pop("screenshot", None) # no need for screenshots here
        final_result.append(doc)
    return final_result

async def get_link_data(link_id: str)-> dict:
    collection = db["links"]
     
    try:
        link_object_id = ObjectId(link_id)
    except: # invalid id format
        return None

    result = await collection.find_one({"_id": link_object_id}, {"_id": 0})

    return result

async def get_links_to_check(scraper_id: str) -> list:
    # select the correct collection
    collection = db["links"]
    
    documents = await collection.find({"scraper_id": scraper_id, "suspicious": ""}).to_list(length=None)
    return [dict({
        "id": str(doc["_id"]),
        "link": doc["link"],
        "profiles": doc["profiles"],
        "suspicious": doc.get("suspicious", ""),
        "state": doc.get("state", ""),
        "manual_check_result": doc.get("manual_check_result", "")
    }) for doc in documents]

async def get_all_links_data() -> list:
    # select the correct collection
    collection = db["links"]
    documents = await collection.find({}).to_list(length=None)

    return [{"id": str(doc["_id"]), **doc} for doc in documents]

async def get_all_sus_links():
    collection = db["links"]
    
    documents = await collection.find({}, {"_id": 0, "link": 1}).to_list(length=None)
    return [doc["link"] for doc in documents]

# UPDATE
async def update_link_state(link_id: str, data: dict):
    # select the correct collection
    collection = db["links"]

    try:
        link_object_id = ObjectId(link_id)
    except: # invalid id format
        return None

    result = await collection.update_one(
        {"_id": link_object_id},
        {
            "$set": data
        }
    )
    return True

async def update_link_data(link_id: str, data: dict):
    # select the correct collection
    collection = db["links"]

    try:
        link_object_id = ObjectId(link_id)
    except: # invalid id format
        return None

    result = await collection.update_one(
        {"_id": link_object_id},
        {
            "$set": data
        }
    )
    return True
