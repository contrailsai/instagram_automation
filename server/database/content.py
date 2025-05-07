
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

# CREATE
async def save_scraped_content(scraper_id: str, content: dict) -> dict:
    # select the correct collection
    collection = db["scraped_content"]

    doc = create_doc(content)
    doc["scraper_id"] = scraper_id
    doc["saved_on"] = datetime.utcnow()

    if content.get("target_app_id", False):
        doc["target_app_id"] = content["target_app_id"]

    result = await collection.insert_one(doc)
    return {"id": str(result.inserted_id)}

async def save_many_scraped_content(scraper_id: str, contents: list) -> None:
    # select the correct collection
    collection = db["scraped_content"]

    documents = []
    # print(len(contents))
    for content in contents:
        doc = create_doc(content)
        doc["scraper_id"] = scraper_id
        doc["saved_on"] = datetime.utcnow()
        documents.append(doc)
    # print(len(documents))        
    await collection.insert_many(documents)

# GET
async def get_reels_data(scraper_id: str) -> dict:
    # select the correct collection
    collection = db["scraped_content"]

    documents = await collection.find({"scraper_id": scraper_id}).to_list(length=None)
    return [dict({
        "id": str(doc["_id"]),
        "code": doc["code"],
        "like_count": doc["like_count"],
        "comment_count": doc["comment_count"],
        "view_count": doc["view_count"],
        "taken_at": doc["taken_at"],
        "username": doc["username"],
        "caption": doc["caption"]
        # "location": doc["location"]
    }) for doc in documents]
