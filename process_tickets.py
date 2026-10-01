import json

from src.triage import process_batch


with open("data/tickets.json", "r", encoding="utf-8") as file:
    tickets = json.load(file)


print(f"Found {len(tickets)} tickets.")
print("Starting batch processing...\n")


results = process_batch(tickets)


print("\nBatch processing finished.")
print(f"Successfully processed: {len(results)} tickets.")