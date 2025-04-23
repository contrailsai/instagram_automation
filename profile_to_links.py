
from server.database import get_profiles_data, save_links_data
import asyncio


async def main():
    
    scraper_id = "67f79ea139a82b72a2f8af50"

    profiles_data = await get_profiles_data(scraper_id)

    links = dict()

    for profile in profiles_data: 
        
        for link in profile["links"]:

            is_there = links.get(link, False)

            if is_there:
                links[link]["profiles"].append(profile["username"])
                links[link]["suspicious"] = links[link]["suspicious"] or profile["is_suspicious"]
            else:
                links[link] = {
                    "profiles": [profile["username"] ],
                    "suspicious" : profile.get("is_suspicious", "")
                }
    
    print(links)
    await save_links_data(links, scraper_id)
    
    return


if __name__ == '__main__':
    asyncio.run(main())
