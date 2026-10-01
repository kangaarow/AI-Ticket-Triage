import json

from src.llm import triage_with_llm


with open("data/tickets.json", "r", encoding="utf-8") as file:
    tickets = json.load(file)


# Test only the first ticket
ticket = tickets[7]

print("Sending ticket to Gemini...")
print()

result = triage_with_llm(ticket)

print("Ticket:")
print(ticket["message"])

print("\nAI Result:")
print(result.model_dump_json(indent=2))