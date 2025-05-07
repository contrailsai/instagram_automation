
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
async def insert_account(account_data: dict) -> dict:
    # select the correct collection
    collection = db["accounts"]

    result = await collection.insert_one(account_data)
    return {"id": str(result.inserted_id), **account_data}

# GET
async def get_account_by_scraper_id(scraper_id: str) -> dict:
    # select the correct collection
    collection = db["accounts"]

    document = await collection.find_one({"scraper_id": scraper_id})
    document["username"] = base64.b64decode(document["username"]).decode("utf-8")
    document["password"] = base64.b64decode(document["password"]).decode("utf-8")

    if document:
        return {"id": str(document["_id"]), **document}
    return None

async def get_unassigned_account() -> dict:
    # select the correct collection
    collection = db["accounts"]
    
    document = await collection.find_one({"scraper_id": None})
    if document:
        return {"id": str(document["_id"]), **document}
    return None

async def get_all_accounts() -> list:
    # select the correct collection
    collection = db["accounts"]

    documents = await collection.find({}).to_list(length=None)
    return [dict({
        "id": str(doc["_id"]),
        "scraper_id": doc.get("scraper_id", None),
    }) for doc in documents]

# UPDATE
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
