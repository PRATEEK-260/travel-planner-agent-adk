"""Guardrails and security checks for the travel planner agent.

They plug into ADK's callback hooks, so every turn passes through four layers:

1. screen_user_input   (before_agent_callback)  blocks prompt injection, unsafe
   requests, oversized input and invalid trip values (0 days, negative budget)
   before any model call is made.
2. redact_pii          (before_model_callback)  removes phone numbers, emails,
   Aadhaar/PAN/card/passport numbers from what is sent to Gemini.
3. validate_tool_args  (before_tool_callback)   checks tool arguments against
   allowed ranges and caps tool calls per turn, so a confused or manipulated
   model can't call tools with bad input or loop forever.
4. filter_model_output (after_model_callback)   stops system-prompt leaks and
   redacts secrets and personal data from the reply.

When a guardrail fires it records its name in session state under
GUARDRAIL_STATE_KEY, which the evaluator reads. Logs only record which rule
fired, never the user's text, so personal data doesn't end up in log files.
"""

import logging
import re
from typing import Any, Optional

from google.adk.models.llm_response import LlmResponse
from google.genai import types

logger = logging.getLogger(__name__)

MAX_INPUT_CHARS = 2000
MIN_DAYS, MAX_DAYS = 1, 30
MAX_TRAVELERS = 20
MAX_BUDGET_INR = 5_000_000
MAX_ENTRY_FEES_INR = 100_000
MAX_TOOL_CALLS_PER_TURN = 12
MAX_CITY_CHARS = 60
MAX_INTERESTS = 10

# Placed in the agent's instruction. If it ever shows up in a reply, the model
# is repeating its instructions, and the reply is replaced.
CANARY = "TP-GUARD-5c1e9a"
# Distinctive phrases from the instruction, as a second leak check.
_INSTRUCTION_FINGERPRINTS = ("work through these steps", "reply in this format", "internal marker")

GUARDRAIL_STATE_KEY = "guardrail"
PII_STATE_KEY = "pii_redactions"
_TOOL_CALLS_STATE_KEY = "temp:tool_calls_this_turn"

_PROMPT_INJECTION = [
    r"\b(ignore|disregard|forget|override)\b.{0,40}\b(previous|prior|above|earlier|all|your|system)\b.{0,20}\b(instructions?|prompts?|rules?|guidelines?)",
    r"\b(reveal|show|print|repeat|output|display|tell me|give me|leak)\b.{0,40}\b(system prompt|instructions|hidden prompt|initial prompt|your prompt|your rules)",
    r"\b(reveal|show|print|give|share|tell|send|what('s| is))\b.{0,30}(api[ _-]?key|secret key|access token|credentials|\.env\b|env file)",
    r"\byou are (now|no longer)\b",
    r"\b(developer|dan|god|jailbreak) mode\b",
    r"\bact as (an? )?(unrestricted|unfiltered|different|evil)\b",
    r"\bpretend (that )?you (have no|are not bound|don't have)\b",
]
_UNSAFE_REQUESTS = [
    r"\bsmuggl\w*",
    r"\b(evade|avoid|bypass|sneak past|trick)\b.{0,30}\b(customs|police|immigration|security check|checkpoint)",
    r"\b(fake|forged?|counterfeit)\b.{0,20}\b(passport|visa|id|identity|documents?|tickets?)",
    r"\b(buy|get|carry|find)\b.{0,20}\b(drugs|cocaine|heroin|meth|weapons?|guns?)\b",
    r"\b(traffick\w*|kidnap\w*)\b",
    r"\b(illegally|without a (visa|permit)|overstay)\b",
]
_NON_POSITIVE_DAYS = r"(?<![\w-])(-\s*)?(\d+)\s*-?\s*(?:day|days|night|nights)\b"
_ZERO_DAYS_WORD = r"\bzero\s*-?\s*(day|days|night|nights)\b"
_NEGATIVE_BUDGET = [
    r"(₹|\brs\.?|\binr\b|\brupees?\b)\s*-\s*\d",
    r"-\s*(₹|\brs\.?|\binr\b)\s*\d",
    r"\bbudget\b[^\d\n]{0,25}?-\s*\d",
    r"\bminus\s+(₹|rs\.?\s*)?\d",
]
_ZERO_BUDGET = r"(\bbudget\b[^\d\n]{0,25}?|₹\s*|\brs\.?\s*)0+(?![\d.,]*[1-9])\b"

_PII_PATTERNS = [
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("AADHAAR", re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b")),
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    ("PHONE", re.compile(r"(?<!\d)(?:\+?91[ -]?)?[6-9]\d{4}[ -]?\d{5}(?!\d)")),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),
    ("PASSPORT", re.compile(r"\b[A-PR-WY][1-9]\d\s?\d{4}[1-9]\b")),
]
_SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    re.compile(r"\bAQ\.[0-9A-Za-z_-]{20,}"),
    re.compile(r"GOOGLE_API_KEY\s*=\s*\S+"),
]


def _text_of(content: Optional[types.Content]) -> str:
    if not content or not content.parts:
        return ""
    return "\n".join(p.text for p in content.parts if p.text)


def _reply(text: str) -> types.Content:
    return types.Content(role="model", parts=[types.Part(text=text)])


def _block(callback_context, rule: str, message: str) -> types.Content:
    logger.warning("Guardrail triggered: %s", rule)
    callback_context.state[GUARDRAIL_STATE_KEY] = rule
    return _reply(message)


def _matches_any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def redact_text(text: str) -> tuple[str, int]:
    """Replaces personal data in text with [REDACTED_<TYPE>] and returns the count."""
    count = 0
    for label, pattern in _PII_PATTERNS:
        text, n = pattern.subn(f"[REDACTED_{label}]", text)
        count += n
    return text, count


# ---------------------------------------------------------------- layer 1


def screen_user_input(callback_context) -> Optional[types.Content]:
    """before_agent_callback: answers directly, without the model, when the
    message is unsafe or the trip values are invalid. Returns None to proceed."""
    callback_context.state[GUARDRAIL_STATE_KEY] = None
    text = _text_of(callback_context.user_content).strip()

    if not text:
        return _block(callback_context, "empty_input",
                      "Tell me where you'd like to go, for how many days, and your budget, and I'll plan the trip.")
    if len(text) > MAX_INPUT_CHARS:
        return _block(callback_context, "input_too_long",
                      f"That message is too long for me to process (limit {MAX_INPUT_CHARS} characters). "
                      "Please send a shorter travel request.")
    if _matches_any(_PROMPT_INJECTION, text):
        return _block(callback_context, "prompt_injection",
                      "I can't change my instructions or share internal details such as prompts or keys. "
                      "I'm happy to help plan a trip in India. Where would you like to go?")
    if _matches_any(_UNSAFE_REQUESTS, text):
        return _block(callback_context, "unsafe_request",
                      "I can't help with anything illegal or unsafe. If you're planning a trip, "
                      "I can suggest an itinerary and a budget for any destination in India.")

    day_values = [(-1 if sign else 1) * int(num) for sign, num in re.findall(_NON_POSITIVE_DAYS, text, re.IGNORECASE)]
    if re.search(_ZERO_DAYS_WORD, text, re.IGNORECASE):
        day_values.append(0)
    if any(d < MIN_DAYS for d in day_values):
        return _block(callback_context, "invalid_days",
                      f"A trip needs at least {MIN_DAYS} day. How many days ({MIN_DAYS}–{MAX_DAYS}) would you like to travel?")
    if any(d > MAX_DAYS for d in day_values):
        return _block(callback_context, "invalid_days",
                      f"I can plan trips of {MIN_DAYS}–{MAX_DAYS} days. Could you choose a shorter duration, "
                      "or split the journey into separate trips?")

    if _matches_any(_NEGATIVE_BUDGET, text) or re.search(_ZERO_BUDGET, text, re.IGNORECASE):
        return _block(callback_context, "invalid_budget",
                      "The budget needs to be a positive amount in rupees (for example ₹15,000). "
                      "What budget would you like me to plan with?")
    return None


# ---------------------------------------------------------------- layer 2


def redact_pii(callback_context, llm_request) -> Optional[LlmResponse]:
    """before_model_callback: strips personal data from the user's messages
    before they are sent to the model. Always lets the call go ahead."""
    total = 0
    for content in llm_request.contents or []:
        if content.role != "user":
            continue
        for part in content.parts or []:
            if part.text:
                part.text, n = redact_text(part.text)
                total += n
    if total:
        logger.info("Redacted %d personal-data item(s) before the model call", total)
        callback_context.state[PII_STATE_KEY] = max(total, callback_context.state.get(PII_STATE_KEY) or 0)
    return None


# ---------------------------------------------------------------- layer 3


def _check_int(args: dict, name: str, low: int, high: int) -> Optional[str]:
    if name not in args:
        return None
    value = args[name]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != int(value):
        return f"{name} must be a whole number"
    if not low <= value <= high:
        return f"{name} must be between {low} and {high}, got {value}"
    return None


def validate_tool_args(tool, args: dict[str, Any], tool_context) -> Optional[dict]:
    """before_tool_callback: rejects out-of-range or malformed arguments and
    caps the number of tool calls per turn. Returns an error result to skip
    the tool, or None to run it."""
    calls = (tool_context.state.get(_TOOL_CALLS_STATE_KEY) or 0) + 1
    tool_context.state[_TOOL_CALLS_STATE_KEY] = calls
    if calls > MAX_TOOL_CALLS_PER_TURN:
        logger.warning("Guardrail triggered: tool_call_limit (%s)", tool.name)
        return {"status": "error", "message": "Tool call limit for this request reached. Answer with what you have."}

    problems = []
    city = args.get("city")
    if city is not None:
        if not isinstance(city, str) or not city.strip():
            problems.append("city must be a non-empty name")
        elif len(city) > MAX_CITY_CHARS or not re.fullmatch(r"[A-Za-z][A-Za-z .,'-]*", city.strip()):
            problems.append("city must be a plain place name (letters, spaces, . , ' -)")
    problems += filter(None, [
        _check_int(args, "days", MIN_DAYS, MAX_DAYS),
        _check_int(args, "travelers", 1, MAX_TRAVELERS),
        _check_int(args, "total_budget_inr", 0, MAX_BUDGET_INR),
        _check_int(args, "planned_entry_fees_inr", 0, MAX_ENTRY_FEES_INR),
    ])
    interests = args.get("interests")
    if interests is not None and (
        not isinstance(interests, list) or len(interests) > MAX_INTERESTS
        or not all(isinstance(i, str) and 0 < len(i) <= 30 for i in interests)
    ):
        problems.append(f"interests must be a list of up to {MAX_INTERESTS} short words")

    if problems:
        logger.warning("Guardrail triggered: invalid_tool_args (%s)", tool.name)
        return {
            "status": "error",
            "message": "Invalid arguments: " + "; ".join(problems),
            "instruction": "Don't guess a value. Ask the user for a valid one.",
        }
    return None


# ---------------------------------------------------------------- layer 4


def filter_model_output(callback_context, llm_response: LlmResponse) -> Optional[LlmResponse]:
    """after_model_callback: replaces replies that leak the instructions and
    redacts secrets and personal data. Returns None when nothing changed."""
    content = llm_response.content
    if not content or not content.parts or not any(p.text for p in content.parts):
        return None

    text = "".join(p.text for p in content.parts if p.text)
    lowered = text.lower()
    if CANARY.lower() in lowered or sum(f in lowered for f in _INSTRUCTION_FINGERPRINTS) >= 2:
        logger.warning("Guardrail triggered: instruction_leak")
        callback_context.state[GUARDRAIL_STATE_KEY] = "instruction_leak"
        return LlmResponse(content=_reply(
            "I can't share my internal instructions. I'm happy to help plan a trip in India, though."))

    changed = False
    for part in content.parts:
        if not part.text:
            continue
        new_text = part.text
        for pattern in _SECRET_PATTERNS:
            new_text = pattern.sub("[REDACTED_SECRET]", new_text)
        new_text, _ = redact_text(new_text)
        if new_text != part.text:
            part.text = new_text
            changed = True
    if changed:
        logger.warning("Guardrail triggered: output_redacted")
        return llm_response
    return None


SAFETY_SETTINGS = [
    types.SafetySetting(category=category, threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE)
    for category in (
        types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
    )
]
