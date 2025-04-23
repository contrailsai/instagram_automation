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
        "scraper_name": scraper_name,
        "active": True,
        "state": "new",
        "is_suspended": False
    }
    result = await collection.insert_one(document)
    return {"id": str(result.inserted_id), **document}

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

async def get_scraper_state(document_id: str) -> str:
    # select the correct collection
    collection = db["scrapers"]

    try:
        object_id = ObjectId(document_id)
    except: # invalid id format
        return None
    
    document = await collection.find_one({"_id": object_id}, {"state": 1, "_id": 0})
    return document["state"]

async def get_all_documents() -> list:
    # select the correct collection
    collection = db["scrapers"]
    
    documents = await collection.find().to_list(length=None)
    return [{"id": str(doc["_id"]), **doc} for doc in documents]

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

    if document:
        document["id"] = str(document_id)
        return document
    return None

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

async def get_all_accounts() -> list:
    # select the correct collection
    collection = db["accounts"]

    documents = await collection.find({}).to_list(length=None)
    return [dict({
        "id": str(doc["_id"]),
        "scraper_id": doc.get("scraper_id", None),
    }) for doc in documents]

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

async def get_profile_data(username: str):
     # select the correct collection
    collection = db["scrape_profiles"]

    result = await collection.find_one(
        {"username": username},
        {"_id": 0}
    )
    return result

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

# SCRAPED CONTENT DATABASE FUNCTIONS

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
    # print(len(contents))
    for content in contents:
        doc = create_doc(content)
        doc["scraper_id"] = scraper_id
        doc["saved_on"] = datetime.utcnow()
        documents.append(doc)
    # print(len(documents))        
    await collection.insert_many(documents)


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

async def create_freq_stats(doc: dict):
    collection = db["keywords_stats"]
    
    result = await collection.insert_one(doc)
    return {"id": str(result.inserted_id)}

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

async def update_freq_stats(scraper_id: str, new_stats: dict):
    # select the correct collection
    collection = db["keywords_stats"]
    
    await collection.update_one(
        {"scraper_id": scraper_id},
        {"$set": {"freq": new_stats}},
        upsert=True
    )
    return


# LINKS

# {
#     "link": "https://....",
#     "profiles": ["username-1", "username2"],
#     "suspicious": "",
#     "state": "",
#     "manual_check_result": ""
# }

async def get_link_data(link_id: str)-> dict:
    collection = db["links"]
     
    try:
        link_object_id = ObjectId(link_id)
    except: # invalid id format
        return None

    result = await collection.find_one({"_id": link_object_id}, {"_id": 0})

    return result

async def get_links_data(scraper_id: str) -> dict:
    # select the correct collection
    collection = db["links"]
    links = set()
    documents = await collection.find({"scraper_id": scraper_id, }, {"_id": 0}).to_list(length=None)
    
    return list(documents)

async def get_all_links_data() -> list:
    # select the correct collection
    collection = db["links"]
    documents = await collection.find({}).to_list(length=None)

    return [{"id": str(doc["_id"]), **doc} for doc in documents]

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