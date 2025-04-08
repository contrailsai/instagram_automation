import os
import json

data = dict()

with open("profiles_links_n_text.json", 'r') as f:
    data = json.load(f)

print("total profiles found = ", len(data))

links = set()

for d in data.values():
    if len(d["links"]) > 0:
        for l in d["links"]:
            links.add(l)
        
links = list(links)

with open("bio_links.txt" , 'w') as f:
    for l in links:
        f.write(f"{l} \n")