from typing import Literal

from pydantic import BaseModel, Field


Urgency = Literal["Critical", "High", "Medium", "Low"]

Category = Literal[
    "Billing",
    "Technical",
    "Account",
    "Feedback",
    "Other",
]

Sentiment = Literal[
    "Angry",
    "Frustrated",
    "Neutral",
    "Happy",
]


class TriageResult(BaseModel):
    urgency: Urgency
    category: Category
    sentiment: Sentiment
    suggested_reply: str = Field(
        min_length=1,
        description="A concise, helpful reply to the customer."
    )