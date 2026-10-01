import json
from pathlib import Path

from src.llm import triage_with_llm


RESULTS_PATH = Path("results/results.json")


def load_existing_results():
    """Load previously saved results.

    Return an empty list if the file does not exist.
    Raise an error if the file exists but cannot be read correctly.
    """
    if not RESULTS_PATH.exists():
        return []

    with open(RESULTS_PATH, "r", encoding="utf-8") as file:
        results = json.load(file)

    if not isinstance(results, list):
        raise ValueError("results/results.json must contain a JSON list.")

    return results


def save_results(results):
    """Save results to disk."""
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(RESULTS_PATH, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)


def process_batch(
    tickets,
    progress_callback=None,
    ticket_ids_to_process=None,
):
    """Process tickets using the LLM.

    Normal mode:
        process_batch(tickets)
        Skips tickets that already have saved results.

    Targeted mode:
        process_batch(tickets, ticket_ids_to_process={6})
        Processes the specified ticket even if it already has a result.
        A successful result replaces the previous result.

    If targeted processing fails, the exception is raised so the UI
    can display an error. The previous saved result remains unchanged.
    """
    results = load_existing_results()

    processed_ids = {
        str(result["ticket_id"])
        for result in results
        if isinstance(result, dict) and "ticket_id" in result
    }

    if ticket_ids_to_process is None:
        # Normal batch processing: only process tickets without results.
        work_tickets = [
            ticket
            for ticket in tickets
            if str(ticket["id"]) not in processed_ids
        ]
        targeted_mode = False

    else:
        # Targeted processing: process only the requested ticket IDs.
        requested_ids = {
            str(ticket_id) for ticket_id in ticket_ids_to_process
        }

        tickets_by_id = {
            str(ticket["id"]): ticket
            for ticket in tickets
        }

        missing_ids = requested_ids - set(tickets_by_id)

        if missing_ids:
            raise ValueError(
                f"Ticket IDs not found in data/tickets.json: "
                f"{', '.join(sorted(missing_ids))}"
            )

        work_tickets = [
            tickets_by_id[ticket_id]
            for ticket_id in requested_ids
        ]

        targeted_mode = True

    total = len(work_tickets)

    if total == 0:
        return results

    completed = 0

    for ticket in work_tickets:
        ticket_id = str(ticket["id"])

        print(f"Processing ticket #{ticket_id}...")

        try:
            # The LLM call stays in the Python backend.
            result = triage_with_llm(ticket)

            result_data = {
                "ticket_id": ticket["id"],
                "message": ticket["message"],
                **result.model_dump(),
            }

            # Remove the old result only after the LLM succeeds.
            updated_results = [
                existing
                for existing in results
                if not (
                    isinstance(existing, dict)
                    and str(existing.get("ticket_id")) == ticket_id
                )
            ]

            updated_results.append(result_data)

            # Save before updating the in-memory results.
            save_results(updated_results)
            results = updated_results

            completed += 1

            print(f"Ticket #{ticket_id} completed.")

            if progress_callback:
                progress_callback(completed, total, ticket_id)

        except Exception as error:
            print(f"Ticket #{ticket_id} failed.")
            print(f"Error: {error}")

            # For a targeted regeneration, let the UI know it failed.
            # The old result has not been removed from the saved file.
            if targeted_mode:
                raise

            # For normal batch processing, continue with other tickets.
            continue

    return results