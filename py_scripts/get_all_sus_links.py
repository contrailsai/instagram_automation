from server.database.database import get_all_sus_ads_links, get_all_sus_links

import asyncio

async def get_combined_sus_links():   
    links_set = set()
    ads_sus_links = await get_all_sus_ads_links() 
    sus_links = await get_all_sus_links()

    print("ads_sus_links", len(ads_sus_links) if ads_sus_links else "No suspicious ad links found")
    print("sus_links", len(sus_links) if sus_links else "No suspicious links found")

    # Add all links to the set
    links_set.update(ads_sus_links)
    links_set.update(sus_links)

    # Write unique links to file
    with open("suspicious_links.txt", "w") as f:
        for link in links_set:
            f.write(link + "\n")

    return

if __name__ == "__main__":
    social_media_keywords = ["youtube", "facebook", "telegram", "instagram", "whatsapp", "wa.me", "t.me", "x.com", "youtu.be", "yt.", "twitter", "flipkart", "ipl"]

    # Read the links from the file
    with open("links.txt", "r") as f:
        lines = f.readlines()

    # Filter out links containing social media keywords
    filtered_links = [
        link for link in lines
        if not any(keyword in link for keyword in social_media_keywords)
    ]

    # Write the filtered links back to the file
    with open("suspicious_links.txt", "w") as f:
        f.writelines(filtered_links)

    print("Filtered suspicious_links.txt", len(filtered_links) if filtered_links else "No links found after filtering")


    # asyncio.run(get_combined_sus_links())