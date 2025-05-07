
from server.database import get_profiles_data, get_reels_data, get_links_data, get_ads_data
import asyncio
import json


async def main():
    
    scraper_id = "67f79ea139a82b72a2f8af50"
    # app_id = "680bc9dd348da74c94aca035"

    profiles_data = await get_profiles_data(scraper_id)
    reels_data = await get_reels_data(scraper_id)
    links_data = await get_links_data(scraper_id)
    ads_data = await get_ads_data(scraper_id)

    with open("profiles_data.json", 'w') as f:
        json.dump(profiles_data, f)

    with open("reels_data.json", 'w') as f:
        json.dump(reels_data, f)

    with open("links_data.json", 'w') as f:
        json.dump(links_data, f)

    with open("ads_data.json", 'w') as f:
        json.dump(ads_data, f)
    
    return


if __name__ == '__main__':
    asyncio.run(main())
