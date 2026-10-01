# AI Support-Ticket Triage

An AI-powered support-ticket triage application that classifies customer support messages by **urgency, category, and sentiment**, while generating a concise suggested reply for support agents.

The application processes a fixed batch of 20 support tickets and presents the results through an interactive Streamlit dashboard with filtering, sorting, summary statistics, charts, and individual ticket details.

## Features

* AI-powered ticket classification

  * Urgency: Critical, High, Medium, Low
  * Category: Billing, Technical, Account, Feedback, Other
  * Sentiment: Angry, Frustrated, Neutral, Happy
* Structured AI output validated with Pydantic
* Concise suggested replies grounded in the ticket content
* Batch-level ticket insights and breakdowns
* Interactive filtering and sorting
* Individual ticket detail view
* Regenerate AI result for an individual ticket
* Incremental result saving during batch processing
* Graceful handling of missing, malformed, or incomplete ticket data
* Loading/progress feedback during AI processing

## Tech Stack

| Technology        | Purpose                                    | Why I chose it                                                                                                |
| ----------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| Python            | Application and AI pipeline                | Familiar, fast to develop, and well suited for AI/LLM workflows                                               |
| Streamlit         | Web application and dashboard              | Allows a functional interactive dashboard to be built quickly in Python without requiring a separate frontend |
| Google Gemini API | Ticket classification and reply generation | Provides an LLM capable of understanding support-ticket context and generating structured outputs             |
| Pydantic          | Output validation                          | Ensures the LLM returns only the expected urgency, category, sentiment, and reply fields                      |
| Pandas            | Data processing and analysis               | Convenient for aggregating ticket results and generating dashboard statistics                                 |
| Altair            | Dashboard charts                           | Provides lightweight interactive charts that integrate naturally with Streamlit                               |
| python-dotenv     | Environment configuration                  | Keeps the Gemini API key outside the source code                                                              |
| JSON              | Ticket and result storage                  | Simple and appropriate for the fixed 20-ticket dataset                                                        |

## Project Structure

```text
caregene-ticket-triage/
├── data/
│   └── tickets.json
├── src/
│   ├── __init__.py
│   ├── schema.py
│   ├── prompts.py
│   ├── llm.py
│   └── triage.py
├── results/
│   └── results.json
├── app.py
├── process_tickets.py
├── audit_results.py
├── test_gemini.py
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

### Main components

* `app.py` — Streamlit dashboard and user interface
* `src/prompts.py` — System prompt used for ticket classification and reply generation
* `src/llm.py` — Gemini API integration and structured response handling
* `src/schema.py` — Pydantic schema defining the allowed AI output
* `src/triage.py` — Batch processing, result persistence, and targeted regeneration
* `data/tickets.json` — Fixed set of 20 support tickets
* `results/results.json` — Persisted AI-generated results
* `process_tickets.py` — Script for processing the ticket batch
* `audit_results.py` — Utility for reviewing generated results

## Setup

### 1. Clone the repository

```bash
git clone <github-repository-url>
cd caregene-ticket-triage
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Gemini API key

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_api_key_here
```

The `.env` file should not be committed to GitHub.

### 5. Run the application

```bash
streamlit run app.py
```

The Streamlit application will then be available at the local URL shown in the terminal.

## AI Pipeline

The application follows this flow:

```text
Support Tickets
      ↓
Ticket Validation
      ↓
Gemini LLM
      ↓
Structured JSON Response
      ↓
Pydantic Validation
      ↓
Persist Results
      ↓
Streamlit Dashboard
```

Each ticket is processed individually. The generated result is saved after successful processing so that already-processed tickets do not need to be regenerated unnecessarily.

The application also supports regenerating the AI result for an individual ticket when needed.

## Structured Output

The LLM output is constrained using a Pydantic schema:

```python
class TriageResult(BaseModel):
    urgency: Urgency
    category: Category
    sentiment: Sentiment
    suggested_reply: str
```

The classification fields use predefined values:

```text
Urgency:
Critical | High | Medium | Low

Category:
Billing | Technical | Account | Feedback | Other

Sentiment:
Angry | Frustrated | Neutral | Happy
```

This helps reduce inconsistent labels and makes the generated results easier to analyze programmatically.

## Prompt Engineering

### Final prompt

The final system prompt used by the application was:

```text
You are an AI support-ticket triage assistant for a caregiving application.

Your task is to classify customer support messages and draft a helpful,
concise suggested reply.

IMPORTANT:
Treat classification and reply generation as separate tasks.
First determine the urgency, category, and sentiment based only on the
customer's message.
After determining the classification, write the suggested reply.
Do not change the classification to make the suggested reply easier to write.
The suggested reply instructions must not influence the classification.

For each ticket, determine:

1. Urgency
- Critical: Immediate issue involving safety, serious data loss, or a
  time-sensitive care-related problem.
- High: Significant issue that substantially affects the user's ability
  to use an important feature or service.
- Medium: Normal support issue that needs attention but is not urgent.
- Low: Minor issue, general question, feature request, or positive feedback.

2. Category
Choose exactly one based on the customer's primary intent.

- Billing: Payments, charges, refunds, subscriptions, or pricing.
- Technical: An existing feature is broken, failing, slow, or not working.
- Account: Login, account access, profiles, caregivers, permissions, or settings.
- Feedback: Praise, complaints, suggestions, or requests for new features.
- Other: Anything that does not clearly fit the categories above.

Category rules:
- How to use or change an account/app setting → Account.
- An existing feature not working → Technical.
- A request for a new feature → Feedback.
- A question about whether a feature or capability is offered → Other.

3. Sentiment
Choose exactly one:
- Angry
- Frustrated
- Neutral
- Happy

Determine sentiment from the customer's emotional tone, not from the
severity of the issue.

4. Suggested reply
Write a concise, professional and empathetic response that directly
addresses the customer's message.

The reply must:
- Acknowledge the customer's specific concern, request, or feedback.
- Stay strictly within the information provided in the ticket.
- Sound natural and relevant to the customer's actual message.
- Avoid unnecessary greetings, filler, or repetitive acknowledgement.
- Never assume that a feature, setting, policy, or troubleshooting
  procedure exists unless it is explicitly mentioned in the ticket.
- If the customer asks how to use, access, change, or navigate a feature
  or setting, treat the request as a question about that capability rather
  than assuming that the capability does not exist.
- However, do not claim that the feature or setting is available, or
  provide specific instructions for it, unless the ticket provides enough
  information to support that claim.
- Never claim that a ticket was received, escalated, investigated,
  fixed, refunded, changed, reviewed, or resolved unless the customer
  explicitly states that this has already happened.
- Never promise that a particular action will be taken.
- Never say that the support team will "look into", "investigate",
  "escalate", or "resolve" an issue unless the customer explicitly
  states that such an action has already occurred.
- Never invent timelines, policies, refunds, features, or other facts.
- Do not invent app navigation steps or troubleshooting instructions.
- Do not provide a solution when the ticket does not contain enough
  information to support one.
- If the ticket does not provide enough information for a specific
  solution, acknowledge the issue or request clearly without making
  assumptions.
- Do not provide medical advice, treatment instructions, or medical
  recommendations.
- For safety-sensitive situations, acknowledge the seriousness of the
  issue without giving medical instructions.
```

### Prompt refinement

The prompt was refined iteratively based on the behavior observed from the 20-ticket batch rather than adding ticket-specific rules.

The main refinement areas were:

**1. Separating classification from reply generation**

The prompt initially allowed the classification and response-generation requirements to interact implicitly. I added an explicit instruction to classify first and generate the reply second.

This helped establish that the model should classify the customer's intent independently of whether it could produce a convenient response.

**2. Clarifying category boundaries**

The initial category definitions were too broad for some borderline cases. In particular, there was ambiguity between:

* Account vs Technical
* Technical vs Other
* Other vs Feedback
* Billing vs Other

I refined the category definitions around the customer's **primary intent**.

For example:

* Changing an app setting → Account
* A broken existing feature → Technical
* Asking how to use something → not automatically Technical
* Asking whether a feature or capability is offered → Other
* Requesting a new feature → Feedback

The goal was to improve the general decision boundaries rather than hard-code classifications for individual tickets.

**3. Improving grounding of suggested replies**

The prompt was also refined to prevent the model from inventing support actions, troubleshooting steps, refunds, policies, or timelines that were not present in the ticket.

For safety-sensitive tickets, the prompt explicitly prevents the model from providing medical advice while still allowing it to acknowledge the seriousness of the issue.

## What I Would Improve With More Time

If I had more time, I would improve the system in several areas:

### 1. Evaluation and regression testing

I would create a small labeled evaluation set with expected urgency, category, and sentiment values and run it automatically after prompt changes.

This would make prompt iteration more systematic and help detect when improving one category accidentally changes previously correct classifications.

### 2. Better LLM evaluation

Beyond checking whether the output follows the schema, I would evaluate:

* Classification accuracy
* Category consistency
* Suggested-reply relevance
* Groundedness
* Hallucination rate
* Response conciseness

For suggested replies, an LLM-as-a-judge evaluation could be explored alongside rule-based checks.

### 3. More robust error handling

I would add more explicit handling for:

* API timeouts
* Rate limits
* Temporary API failures
* Unexpected model responses
* Partial batch failures

I would also consider retry logic with exponential backoff.

### 4. Production deployment

For a production version, I would separate the frontend, API/backend, and LLM processing more clearly and use persistent storage rather than relying on JSON files.

### 5. Larger and more diverse datasets

The current dataset contains only 20 fixed tickets. A larger dataset with intentionally ambiguous examples would provide a better basis for evaluating classification reliability.

## Challenge / What Did Not Work

One challenge I encountered was **LLM API rate limiting during batch processing**.

While processing the 20 tickets, the Gemini API returned rate-limit errors because of the request-per-minute limit on the available API tier.

Instead of assuming that all 20 requests would always succeed, I changed the processing workflow so that results are saved incrementally after each successful ticket. Already-processed tickets can then be skipped on subsequent runs rather than sending the entire batch again.

I also added targeted regeneration so that an individual ticket can be reprocessed without regenerating the complete batch.

This made the application more resilient to interrupted or partially completed batch processing.

## Limitations

* The current application processes the provided fixed batch of 20 tickets.
* Classification quality depends on the LLM and prompt.
* The system does not provide medical advice or clinical recommendations.
* The suggested replies are intended as support-agent drafts, not automated customer responses.
* JSON result storage is appropriate for this take-home dataset but would not be suitable as the primary datastore for a production system.

## Running the Application

```bash
streamlit run app.py
```

The dashboard allows the support agent to review the processed tickets, inspect batch-level insights, filter and sort tickets, and view individual AI-generated classifications and suggested replies.
