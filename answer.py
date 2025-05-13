import json
from difflib import get_close_matches

# Load the data from the JSON file
with open("fiu_onestop_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    

# Extract just the content pieces
documents = [item["content"] for item in data if "content" in item and item["content"]]

print("Ask PantherBot (type 'exit' to quit):")
while True:
    user_input = input("Ask PantherBot: ").strip().lower()
    if user_input == "exit":
        break

    # Find best matching content
    match = get_close_matches(user_input, documents, n=1, cutoff=0.3)
    
    if match:
        print("💬", match[0])
    else:
        print("⚠️ Sorry, PantherBot doesn't have an answer for that. Try rephrasing or check official FIU websites.")
        print("💬", " ".join(documents))