from __future__ import annotations

import json
import re
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.core.config import settings


class Intent(BaseModel):
    product_query: str = "Product A"
    quantity: int | None = None
    horizon: str = "next_month"
    lead_time_days_max: int = 31
    objective: str = "min_cost_low_risk"
    low_risk: bool = True
    notes: str = ""


class LLMClient(Protocol):
    def complete_json(self, system: str, user: str) -> dict[str, Any]: ...


class MockLLM:
    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        qty = None
        # Handle word numbers
        words_map = {
            "five thousand": 5000,
            "ten thousand": 10000,
            "twenty thousand": 20000,
        }
        for w, val in words_map.items():
            if w in user.lower():
                qty = val
                break

        if qty is None:
            # Handle '10k', '50k' format
            km = re.search(r"\b(\d+)\s*k\b", user, re.I)
            if km:
                qty = int(km.group(1)) * 1000

        if qty is None:
            # Handle standard numbers with commas or plain digits
            m = re.search(r"(\d{1,3}(?:,\d{3})+|\d+)\s*(?:units|pieces|pkgs)?", user, re.I)
            if m:
                val = int(m.group(1).replace(",", ""))
                if val >= 100:  # Avoid matching days or percentages like 15%
                    qty = val

        product = "Product A"
        pm = re.search(r"product\s+([A-Ja-j])\b", user, re.I)
        if pm:
            product = f"Product {pm.group(1).upper()}"
        else:
            nm = re.search(r"\b(PROD-[A-J])\b", user, re.I)
            if nm:
                letter = nm.group(1).upper().split("-")[1]
                product = f"Product {letter}"

        low_risk = any(
            k in user.lower()
            for k in ["low risk", "low-risk", "minimal risk", "minimum risk", "safe", "reliability", "avoid high risk", "high reliability"]
        )

        if "lowest cost" in user.lower() or "cheapest" in user.lower() or "minimize cost" in user.lower() or "lowest landed cost" in user.lower() or "minimal cost" in user.lower():
            objective = "min_cost"
        elif "fast" in user.lower() or "transit time" in user.lower() or "fast delivery" in user.lower() or "deliver" in user.lower() or "lead time" in user.lower():
            objective = "min_time"
        elif "minimizing risk" in user.lower() or "minimal risk" in user.lower() or "minimum risk" in user.lower() or "lowest risk" in user.lower():
            objective = "min_risk"
        else:
            objective = "min_cost"


        if "urgent" in user.lower() or "asap" in user.lower():
            horizon = "urgent"
        elif "quarter" in user.lower() or "q3" in user.lower() or "q4" in user.lower():
            horizon = "next_quarter"
        else:
            horizon = "next_month"

        return Intent(
            product_query=product,
            quantity=qty,
            horizon=horizon,
            lead_time_days_max=31,
            objective=objective,
            low_risk=low_risk,
            notes="Parsed by robust rule/regex engine.",
        ).model_dump()



class GeminiLLM:
    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        from google import genai

        client = genai.Client(api_key=settings.resolved_gemini_key)
        prompt = (
            f"{system}\n\nUser request:\n{user}\n\n"
            "Return ONLY JSON with keys: product_query, quantity, horizon, "
            "lead_time_days_max, objective, low_risk, notes."
        )
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
        )
        text = response.text or "{}"
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text).rstrip("`").strip()
        data = json.loads(text)
        return Intent.model_validate(data).model_dump()


def get_llm() -> LLMClient:
    provider = settings.effective_llm_provider
    if provider == "gemini" and settings.resolved_gemini_key:
        return GeminiLLM()
    return MockLLM()


def parse_intent(query: str) -> Intent:
    llm = get_llm()
    system = (
        "You extract supply-chain planning intent. "
        "quantity is an integer or null if not stated. "
        "objective is one of min_cost, min_cost_low_risk, min_time, balanced. "
        "low_risk is true if the user wants low risk. "
        "Do not invent demand numbers that were not requested."
    )
    try:
        data = llm.complete_json(system, query)
        return Intent.model_validate(data)
    except Exception:
        return Intent.model_validate(MockLLM().complete_json(system, query))
