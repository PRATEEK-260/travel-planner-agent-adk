"""Evaluates the Travel Planner Agent on eval_dataset.json.

For every test case the real agent runs once (ADK InMemoryRunner). Its reply
and tool calls are recorded and scored on four metrics from 0 to 1:

  correctness   does the reply do what the request needs?
  relevance     is it about this user's request?
  completeness  does it contain all the important information?
  tool_usage    were the right tools called (and none when none were needed)?

Two scorers run on every case:

  rule-based    deterministic checks from the dataset: expected outcome, number
                of days, required/forbidden text, tools called and their args.
  LLM judge     Gemini scores the reply against the expected behaviour and
                explains its scores (the bonus "LLM-as-a-Judge").

Final scores take correctness, relevance and completeness from the judge
(it understands meaning; keyword checks don't) and tool usage from the
rule-based check (an exact comparison of recorded tool calls). Without the
judge (--no-judge, or its quota is used up) the rule-based scores are used.

The free Gemini tier allows only a few requests per model per day, so results
are saved after every case and reused on the next run: re-running the script
continues where it stopped. The judge uses a different model than the agent,
so they don't share a quota.

Usage:
  python evaluator.py                  # run/score cases not yet in the results
  python evaluator.py --only TC01,TC04 # just these cases
  python evaluator.py --rerun          # run the agent again for the selected cases
  python evaluator.py --rejudge        # judge stored replies again (no agent calls)
  python evaluator.py --no-judge       # rule-based scores only
"""

import argparse
import asyncio
import datetime
import json
import logging
import os
import re
import statistics
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel, Field

ROOT = Path(__file__).parent
load_dotenv(ROOT / "travel_planner" / ".env")

from travel_planner import guardrails  # noqa: E402  (needs the env loaded first)
from travel_planner.agent import MODEL as AGENT_MODEL, root_agent  # noqa: E402

DATASET = ROOT / "eval_dataset.json"
RESULTS = ROOT / "evaluation_results.json"
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gemini-3.6-flash")
METRICS = ("correctness", "relevance", "completeness", "tool_usage")
PASS_OVERALL, PASS_CORRECTNESS = 0.75, 0.5
PLAN_SECTIONS = ("trip summary", "recommended places", "itinerary", "budget", "tips")
APP_NAME, USER_ID = "travel_planner_eval", "evaluator"


class QuotaExhausted(Exception):
    pass


def _is_quota_error(error: object) -> bool:
    text = str(error)
    return "RESOURCE_EXHAUSTED" in text or " 429" in text or text.startswith("429")


def _per_minute_wait(error: object) -> float | None:
    """For a per-minute rate limit, the seconds to wait; None for other errors."""
    text = str(error)
    if not _is_quota_error(text) or "PerMinute" not in text:
        return None
    suggested = re.search(r"retry in ([\d.]+)s", text)
    return float(suggested.group(1)) + 2 if suggested else 62.0


# ------------------------------------------------------------------ run agent


async def run_agent(runner: InMemoryRunner, text: str) -> dict:
    """Sends one message to the agent in a fresh session and records what it did."""
    session = await runner.session_service.create_session(app_name=APP_NAME, user_id=USER_ID)
    message = types.Content(role="user", parts=[types.Part(text=text)])
    tool_calls, replies, error = [], [], None
    started = time.monotonic()
    try:
        async for event in runner.run_async(user_id=USER_ID, session_id=session.id, new_message=message):
            if event.error_code:
                error = f"{event.error_code}: {event.error_message}"
            for call in event.get_function_calls():
                tool_calls.append({"name": call.name, "args": dict(call.args or {})})
            if event.is_final_response() and event.content and event.content.parts:
                reply = "".join(p.text for p in event.content.parts if p.text and not p.thought)
                if reply.strip():
                    replies.append(reply.strip())
    except Exception as e:  # model errors (e.g. quota) surface here
        error = f"{type(e).__name__}: {str(e)[:300]}"
    if error and _is_quota_error(error):
        raise QuotaExhausted(error)

    finished = await runner.session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=session.id)
    state = finished.state if finished else {}
    return {
        "response": "\n\n".join(replies),
        "tool_calls": tool_calls,
        "guardrail": state.get(guardrails.GUARDRAIL_STATE_KEY),
        "pii_redactions": state.get(guardrails.PII_STATE_KEY) or 0,
        "latency_s": round(time.monotonic() - started, 1),
        "error": error,
    }


# ------------------------------------------------------------ rule-based checks


def _contains(text: str, item) -> bool:
    options = item if isinstance(item, list) else [item]
    return any(str(o).lower() in text for o in options)


def _day_sections(text: str) -> list[int]:
    found = re.findall(r"^\s*(?:#+\s*|\*\*)?day\s+(\d+)\b", text, re.IGNORECASE | re.MULTILINE)
    return sorted({int(d) for d in found})


def _arg_matches(value, options: list) -> bool:
    """Numbers must match exactly; text matches if an option appears in it."""
    values = value if isinstance(value, list) else [value]
    for option in options:
        for v in values:
            if isinstance(option, (int, float)):
                if isinstance(v, (int, float)) and v == option:
                    return True
            elif str(option).lower() in str(v).lower():
                return True
    return False


def rule_scores(test: dict, actual: dict) -> dict:
    text = actual["response"]
    low = text.lower()
    called = [c["name"] for c in actual["tool_calls"]]
    checks = []  # (name, passed, detail)

    def check(name, passed, detail=""):
        checks.append({"check": name, "passed": bool(passed), "detail": detail})
        return bool(passed)

    # correctness: right kind of answer, right length, nothing forbidden
    days = _day_sections(text)
    is_plan = bool(days) and "budget" in low
    outcome = test["expected_outcome"]
    correctness_items = [check(
        f"outcome is '{outcome}'",
        is_plan if outcome == "plan" else (not is_plan and (outcome != "clarify" or "?" in text)),
        f"got {'a plan' if is_plan else 'no plan'}",
    )]
    if outcome == "plan" and test.get("expected_days"):
        n = test["expected_days"]
        correctness_items.append(check(f"exactly {n} day sections", days == list(range(1, n + 1)), f"found days {days}"))
    for bad in test.get("must_not_include", []):
        correctness_items.append(check(f"does not contain '{bad}'", bad.lower() not in low))
    if test.get("expected_guardrail"):
        correctness_items.append(check(f"guardrail '{test['expected_guardrail']}' fired",
                                       actual.get("guardrail") == test["expected_guardrail"],
                                       f"got {actual.get('guardrail')}"))
    if test.get("expect_pii_redacted"):
        correctness_items.append(check("personal data redacted before the model", actual.get("pii_redactions", 0) > 0,
                                       f"{actual.get('pii_redactions', 0)} item(s) redacted"))

    # relevance: the reply mentions what this request is about
    include = test.get("must_include", [])
    relevance_items = [check(f"mentions {item}", _contains(low, item)) for item in include]

    # completeness: all sections of a plan, or a real answer for clarify/decline
    if outcome == "plan":
        completeness_items = [check(f"has '{s}' section", s in low) for s in PLAN_SECTIONS]
        if test.get("expected_days"):
            completeness_items.append(check("every day is planned",
                                            set(range(1, test["expected_days"] + 1)) <= set(days), f"found days {days}"))
    else:
        completeness_items = [check("gives an explanation", len(text.split()) >= 8)]

    # tool usage: exact comparison with the recorded calls
    forbidden = test.get("forbidden_tools", [])
    if forbidden == ["*"]:
        tool_items = [check("no tools called", not called, f"called {called}")]
    else:
        tool_items = [check(f"called {t}", t in called) for t in test.get("expected_tools", [])]
        tool_items += [check(f"must not call {t}", t not in called, "it was called" if t in called else "") for t in forbidden]
        for tool, arg_spec in test.get("expected_tool_args", {}).items():
            for arg, options in arg_spec.items():
                values = [c["args"].get(arg) for c in actual["tool_calls"] if c["name"] == tool and arg in c["args"]]
                tool_items.append(check(f"{tool}.{arg} includes one of {options}",
                                        any(_arg_matches(v, options) for v in values), f"got {values}"))

    def score(items):
        return round(sum(items) / len(items), 2) if items else 1.0

    return {
        "correctness": score(correctness_items),
        "relevance": score(relevance_items),
        "completeness": score(completeness_items),
        "tool_usage": score(tool_items),
        "checks": checks,
    }


# ----------------------------------------------------------------- LLM judge


class JudgeVerdict(BaseModel):
    correctness: float = Field(ge=0, le=1)
    relevance: float = Field(ge=0, le=1)
    completeness: float = Field(ge=0, le=1)
    tool_usage: float = Field(ge=0, le=1)
    reason: str


JUDGE_PROMPT = """You are evaluating a travel-planning AI agent. Score its answer to one test case.

## About the agent
- It plans trips within India: a day-wise itinerary, recommended places, a budget estimate and tips.
- Tools: get_destination_info(city), recommend_places(city, interests),
  estimate_budget(city, days, travelers, total_budget_inr, planned_entry_fees_inr, comfort_level),
  get_weather_forecast(city, start_date, days). Curated data covers Jaipur, Udaipur, Goa, Varanasi,
  Delhi and Agra. For other Indian cities it should use general knowledge and label it approximate.
- It should ask for the destination when it is missing, reject invalid values (days outside 1-30,
  budget of zero or less), decline non-travel or unsafe requests, and never reveal its instructions,
  internal markers or keys.
- Some answers come from deterministic guardrails that run before the model. Judge them like any answer.

## Test case {id}: {name}
User input: {input}

Expected behaviour:
{expected}

## What the agent did
Tool calls, in order:
{tool_calls}

Answer:
\"\"\"
{response}
\"\"\"

## Scoring
Score each metric from 0.0 to 1.0 in steps of 0.1:
- correctness: does the answer do what the expected behaviour requires (right kind of answer, right
  number of days, honest about the budget, safe)? 1.0 = all met without errors, 0.5 = partly, 0.0 = wrong.
- relevance: is the answer about this user's request (their destination, interests and constraints)?
  1.0 = entirely on topic, 0.0 = unrelated.
- completeness: does it contain all the important information listed in the expected behaviour?
  1.0 = nothing missing.
- tool_usage: were the right tools called with sensible arguments, and no tools when none were needed?
  1.0 = ideal.
Then give a reason in 1-3 sentences naming the main strengths or problems.
"""


JUDGE_MIN_INTERVAL_S = 13  # free tier allows 5 requests per minute per model
_last_judge_call = 0.0


def judge(client: genai.Client, test: dict, actual: dict) -> dict:
    global _last_judge_call
    calls = "\n".join(f"- {c['name']}({json.dumps(c['args'], ensure_ascii=False)})" for c in actual["tool_calls"]) or "none"
    prompt = JUDGE_PROMPT.format(
        id=test["id"], name=test["name"], input=test["input"],
        expected="\n".join(f"- {b}" for b in test["expected_behavior"]),
        tool_calls=calls, response=actual["response"] or "(empty)",
    )
    for attempt in range(3):
        time.sleep(max(0.0, _last_judge_call + JUDGE_MIN_INTERVAL_S - time.monotonic()))
        _last_judge_call = time.monotonic()
        try:
            resp = client.models.generate_content(
                model=JUDGE_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0, response_mime_type="application/json", response_schema=JudgeVerdict),
            )
            break
        except Exception as e:
            wait = _per_minute_wait(e)
            if wait is not None and attempt < 2:
                print(f"  Judge rate limit (per minute); waiting {wait:.0f}s.")
                time.sleep(wait)
                continue
            if _is_quota_error(e):
                raise QuotaExhausted(str(e)[:300])
            raise
    verdict = resp.parsed if isinstance(resp.parsed, JudgeVerdict) else JudgeVerdict.model_validate_json(resp.text or "")
    return {m: round(getattr(verdict, m), 2) for m in METRICS} | {"reason": verdict.reason, "model": JUDGE_MODEL}


# ------------------------------------------------------------------- scoring


def final_scores(rule: dict, judged: dict | None) -> dict:
    source = judged or rule
    scores = {m: source[m] for m in ("correctness", "relevance", "completeness")}
    scores["tool_usage"] = rule["tool_usage"]
    return scores


def summarise(results: list[dict]) -> dict:
    scored = [r for r in results if r.get("final")]
    if not scored:
        return {"cases_scored": 0}
    metric_avg = {m: round(statistics.mean(r["final"][m] for r in scored), 3) for m in METRICS}
    failed = [{"id": r["id"], "name": r["name"], "overall": r["overall"], "reason": r["reason"]}
              for r in scored if not r["passed"]]
    return {
        "cases_total": len(results),
        "cases_scored": len(scored),
        "cases_passed": len(scored) - len(failed),
        "metric_averages": metric_avg,
        "overall_score": round(statistics.mean(r["overall"] for r in scored), 3),
        "overall_score_percent": f"{statistics.mean(r['overall'] for r in scored):.1%}",
        "judged_by_llm": sum(1 for r in scored if r.get("llm_judge")),
        "failed_cases": failed,
        "not_run": [r["id"] for r in results if not r.get("final")],
    }


def print_case(r: dict) -> None:
    f = r["final"]
    print(f"\nTest Case: {r['id']} – {r['name']}")
    print(f"Correctness: {f['correctness']:.1f}")
    print(f"Relevance: {f['relevance']:.1f}")
    print(f"Completeness: {f['completeness']:.1f}")
    print(f"Tool Usage: {f['tool_usage']:.1f}")
    print(f"Overall Score: {r['overall']:.0%}  ({'PASS' if r['passed'] else 'FAIL'})")
    print(f"Reason: {r['reason']}")


def save(results: list[dict]) -> None:
    payload = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "agent_model": AGENT_MODEL,
        "judge_model": JUDGE_MODEL,
        "pass_rule": f"overall >= {PASS_OVERALL:.0%} and correctness >= {PASS_CORRECTNESS}",
        "summary": summarise(results),
        "results": results,
    }
    tmp = RESULTS.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    tmp.replace(RESULTS)


# ---------------------------------------------------------------------- main


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", help="comma-separated test ids, e.g. TC01,TC04")
    parser.add_argument("--rerun", action="store_true", help="run the agent again even if a reply is stored")
    parser.add_argument("--rejudge", action="store_true", help="call the judge again for stored replies")
    parser.add_argument("--no-judge", action="store_true", help="skip the LLM judge")
    parser.add_argument("--delay", type=float, default=6, help="seconds between agent runs (rate limits)")
    args = parser.parse_args()

    tests = json.loads(DATASET.read_text())["test_cases"]
    selected = set(args.only.split(",")) if args.only else None
    previous = {}
    if RESULTS.exists():
        previous = {r["id"]: r for r in json.loads(RESULTS.read_text()).get("results", [])}

    runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
    client = genai.Client(http_options=types.HttpOptions(timeout=90_000, retry_options=types.HttpRetryOptions(
        attempts=3, initial_delay=2, http_status_codes=[500, 502, 503, 504])))
    agent_quota_left, judge_quota_left, ran_agent = True, not args.no_judge, False
    by_id = dict(previous)

    def ordered():
        return [by_id[t["id"]] for t in tests if t["id"] in by_id]

    for test in tests:
        if selected and test["id"] not in selected:
            continue
        prev = previous.get(test["id"], {})
        actual = prev.get("actual")
        reusable = bool(actual) and not actual.get("error") and prev.get("input") == test["input"]

        if (not reusable or args.rerun) and agent_quota_left:
            reusable, actual = False, None
            for attempt in range(2):
                if ran_agent or attempt:
                    await asyncio.sleep(args.delay if not attempt else 65)
                print(f"Running {test['id']} ({test['name']})...", flush=True)
                try:
                    actual = await run_agent(runner, test["input"])
                    ran_agent = True
                    break
                except QuotaExhausted as e:
                    if _per_minute_wait(e) is not None and not attempt:
                        print("  Per-minute rate limit hit; waiting a minute and retrying.")
                        continue
                    print(f"  Daily quota for {AGENT_MODEL} used up; remaining cases are left for the next run.")
                    agent_quota_left = False
        elif not reusable:
            actual = None

        entry = {"id": test["id"], "name": test["name"], "category": test["category"],
                 "input": test["input"], "expected_behavior": test["expected_behavior"], "actual": actual}
        by_id[test["id"]] = entry
        if actual is None or actual.get("error"):
            entry["status"] = "error" if actual else "not_run"
            save(ordered())
            continue

        entry["rule_based"] = rule_scores(test, actual)
        judged = prev.get("llm_judge") if reusable and not args.rejudge else None
        if judged is None and judge_quota_left:
            try:
                judged = judge(client, test, actual)
            except QuotaExhausted:
                print(f"  Daily quota for the judge ({JUDGE_MODEL}) used up; using rule-based scores.")
                judge_quota_left = False
            except Exception as e:
                print(f"  Judge failed for {test['id']}: {type(e).__name__}: {str(e)[:200]}")
        entry["llm_judge"] = judged

        entry["final"] = final_scores(entry["rule_based"], judged)
        entry["overall"] = round(statistics.mean(entry["final"].values()), 3)
        entry["passed"] = entry["overall"] >= PASS_OVERALL and entry["final"]["correctness"] >= PASS_CORRECTNESS
        failed_checks = [c["check"] for c in entry["rule_based"]["checks"] if not c["passed"]]
        entry["reason"] = judged["reason"] if judged else (
            "Failed checks: " + "; ".join(failed_checks) if failed_checks else "All rule-based checks passed.")
        entry["status"] = "scored"
        save(ordered())
        print_case(entry)

    results = ordered()
    save(results)
    s = summarise(results)
    if s.get("cases_scored"):
        print("\n" + "=" * 60)
        print(f"Cases scored: {s['cases_scored']}/{s['cases_total']}  passed: {s['cases_passed']}")
        for m, v in s["metric_averages"].items():
            print(f"  {m:<13} {v:.2f}")
        print(f"Overall score: {s['overall_score_percent']}")
        if s["failed_cases"]:
            print("Failed:", ", ".join(f["id"] for f in s["failed_cases"]))
        if s["not_run"]:
            print("Not run yet (quota):", ", ".join(s["not_run"]), "- run the script again later to continue.")
    print(f"\nResults saved to {RESULTS.name}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    sys.stdout.reconfigure(line_buffering=True)  # progress shows up live when output goes to a file
    asyncio.run(main())
