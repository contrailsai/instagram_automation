
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

# TARGATED APPS

# {
#     "scraper_id": "",
#     "Keyword": ["govindia"],
#     "link_contains_words": ["govindia365"],
#     "app_name": "govindia365",
# }

async def get_targeted_apps(scraper_id: str) -> dict:
    # select the correct collection
    collection = db["targeted_apps"]
    result = await collection.find({"scraper_id": scraper_id}, {"_id": 0}).to_list(length=None)
    return result

async def get_targeted_app(app_id: str) -> dict:
    # select the correct collection
    collection = db["targeted_apps"]

    try:
        app_object_id = ObjectId(app_id)
    except: # invalid id format
        return None
    result = await collection.find_one({"_id": app_object_id}, {"_id": 0})

    return result

async def update_targeted_app(target_app_id: str, data: dict) -> dict:
    # select the correct collection
    collection = db["targeted_apps"]

    try:
        scraper_object_id = ObjectId(target_app_id)
    except: # invalid id format
        return None

    result = await collection.update_one(
        {"scraper_id": scraper_object_id},
        {
            "$set": data
        },
        upsert=True
    )
    return True

async def insert_targeted_app( data ) -> dict:
    # select the correct collection
    collection = db["targeted_apps"]
    data = dict(data)

    doc = await collection.insert_one(data)
    return True

async def get_targeted_app_profiles(app_id: str) -> list:
    # select the correct collection
    collection = db["scrape_profiles"]
    profiles = await collection.find({"targeted_app_id": app_id}, {"_id": 0}).to_list(length=None)

    return profiles