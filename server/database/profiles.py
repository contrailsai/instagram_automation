
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

# CREATE
async def add_profile(scraper_id: str, username: str, targeted_app_id: str = "") -> dict:
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

    if targeted_app_id!= "":
        profile["targeted_app_id"] = targeted_app_id

    result = await collection.insert_one(profile)
    return {"id": str(result.inserted_id)}

# GET
async def get_profile_data(username: str):
     # select the correct collection
    collection = db["scrape_profiles"]

    result = await collection.find_one(
        {"username": username},
        {"_id": 0}
    )
    return result

async def get_profiles_data(scraper_id: str) -> dict:
        # select the correct collection
    collection = db["scrape_profiles"]

    documents = await collection.find({"scraper_id": scraper_id, "scraped": True}).to_list(length=None)
    return [dict({
        "id": str(doc["_id"]),
        "username": doc["username"],
        "bio": doc["bio"],
        "links": doc["links"],
        "is_suspicious": doc.get("is_suspicious", "")
    }) for doc in documents]

async def get_unscraped_profiles(scraper_id: str) -> list:
    # select the correct collection
    collection = db["scrape_profiles"]

    documents = await collection.find({"scraper_id": scraper_id, "scraped": False}, {"username": 1, "_id": 0}).to_list(length=None)
    return [doc["username"] for doc in documents]

async def profiles_with_links(scraper_id: str) -> list:
    collection = db["scrape_profiles"]

    documents = await collection.find(
        {"scraper_id": scraper_id, "links": {"$exists": True, "$ne": []}, "is_suspicious": {"$exists": False}},
        {"username": 1, "links": 1, "_id": 0}
    ).to_list(length=None)
    
    response = []
    for doc in documents:
        response.append({
            "username": doc["username"],
            "links": doc["links"],
        })

    return response

# UPDATE
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

async def update_profile_data(username: str, data: dict):
     # select the correct collection
    collection = db["scrape_profiles"]

    result = await collection.update_one(
        {"username": username},
        {
            "$set": data
        }
    )
    return True
