import json
from collections import Counter


RESULTS_PATH = "results/results.json"


with open(RESULTS_PATH, "r", encoding="utf-8") as file:
    results = json.load(file)


print(f"Total results: {len(results)}")
print("=" * 60)


print("\nURGENCY")
print(Counter(result["urgency"] for result in results))


print("\nCATEGORY")
print(Counter(result["category"] for result in results))


print("\nSENTIMENT")
print(Counter(result["sentiment"] for result in results))


print("\n" + "=" * 60)
print("INDIVIDUAL RESULTS")
print("=" * 60)


for result in results:
    print(f"\nTicket #{result['ticket_id']}")
    print(f"Urgency:   {result['urgency']}")
    print(f"Category:  {result['category']}")
    print(f"Sentiment: {result['sentiment']}")
    print(f"Reply:     {result['suggested_reply']}")