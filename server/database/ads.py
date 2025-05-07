
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

# ADS
# {
#     scraper_id,
#     link,
#     code,
#     like_count,
#     comment_count,
#     profile,
#     caption,
#     link_text,
# }

async def insert_ads_data(scraper_id: str, data) -> dict:
    # select the correct collection
    collection = db["ads"]
    
    for ad in data:

        ad_data = dict({
            "scraper_id": scraper_id,
            "link": ad["link"],
            "code": ad["code"],
            "like_count": ad["like_count"],
            "comment_count": ad["comment_count"],
            "profile": ad["user"]["username"],
            "caption": ad["caption"],
            "link_text": ad["link_text"]
        })

        result = await collection.insert_one(ad_data)
    return True

async def update_ad_data(ad_id: str, data: dict) -> dict:
    # select the correct collection
    collection = db["ads"]

    try:
        ad_object_id = ObjectId(ad_id)
    except: # invalid id format
        return None

    result = await collection.update_one(
        {"_id": ad_object_id},
        {
            "$set": data
        }
    )
    return True

async def get_ads_data(scraper_id: str) -> dict:
    # select the correct collection
    collection = db["ads"]
    
    documents = await collection.find({"scraper_id": scraper_id}).to_list(length=None)
    return [dict({
        "id": str(doc["_id"]),
        "link": doc["link"],
        "code": doc["code"],
        "like_count": doc["like_count"],
        "comment_count": doc["comment_count"],
        "profile": doc["profile"],
        "caption": doc["caption"],
        "link_text": doc["link_text"],
        "screenshot": doc["screenshot"],
        "filtered_link": doc["filtered_link"]
    }) for doc in documents]

async def get_all_non_filtered_ads(scraper_id: str) -> dict:
    # select the correct collection
    collection = db["ads"]
    
    documents = await collection.find({"scraper_id": scraper_id, "filtered_link": {"$exists": False} }).to_list(length=None)
    return [dict({
        "id": str(doc["_id"]),
        "link": doc["link"],
        "code": doc["code"],
        "like_count": doc["like_count"],
        "comment_count": doc["comment_count"],
        "profile": doc["profile"],
        "caption": doc["caption"],
        "link_text": doc["link_text"]
    }) for doc in documents]

async def get_all_sus_ads_links():
    collection = db["ads"]
    documents = await collection.find({}, {"_id": 0, "filtered_link": 1}).to_list(length=None)
    return [doc["filtered_link"] for doc in documents if "filtered_link" in doc]
