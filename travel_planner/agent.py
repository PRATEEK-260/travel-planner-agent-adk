"""Personal Travel Planner Agent built with Google ADK.

The agent turns a free-form travel request ("3 days in Jaipur, ₹15,000,
I like history and food") into a day-wise itinerary with a budget estimate.

Facts (places, fees, typical costs) come from the curated DESTINATIONS table
through tools, so the numbers in the budget are computed, not guessed by the
model. For cities outside the table the agent falls back to its own general
knowledge and says so. Live weather comes from get_weather_forecast, which
calls the free Open-Meteo API (no key needed).
"""

import datetime
import json
import os
import urllib.parse
import urllib.request

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types

MODEL = os.getenv("TRAVEL_AGENT_MODEL", "gemini-3.5-flash-lite")

# Typical per-person costs in INR. Stay is per room per night (shared by up to
# 2 travellers); food and local transport are per person per day.
COMFORT_LEVELS = {
    "budget": {"stay": 1200, "food": 600, "transport": 400},
    "mid": {"stay": 2800, "food": 1100, "transport": 800},
    "premium": {"stay": 7500, "food": 2500, "transport": 1800},
}

DESTINATIONS = {
    "jaipur": {
        "state": "Rajasthan",
        "best_time": "October to March",
        "getting_around": "Auto-rickshaws, Ola/Uber, or a hired cab for the day (~₹2,000).",
        "cost_multiplier": 1.0,
        "tip": "Buy the composite ticket (₹1,000 foreigners / ₹300 Indians) covering Amber, Nahargarh, Hawa Mahal, Jantar Mantar and Albert Hall.",
        "places": [
            {"name": "Amber Fort", "tags": ["history", "architecture"], "fee": 100, "hours": 3, "area": "Amer"},
            {"name": "Jaigarh Fort", "tags": ["history"], "fee": 150, "hours": 1.5, "area": "Amer"},
            {"name": "Nahargarh Fort (sunset)", "tags": ["history", "views"], "fee": 50, "hours": 2, "area": "Amer"},
            {"name": "Panna Meena ka Kund", "tags": ["architecture", "photography"], "fee": 0, "hours": 0.5, "area": "Amer"},
            {"name": "City Palace", "tags": ["history", "architecture", "museum"], "fee": 200, "hours": 2, "area": "Old City"},
            {"name": "Jantar Mantar", "tags": ["history", "science"], "fee": 50, "hours": 1, "area": "Old City"},
            {"name": "Hawa Mahal", "tags": ["history", "architecture"], "fee": 50, "hours": 1, "area": "Old City"},
            {"name": "Johari & Bapu Bazaar", "tags": ["shopping", "food"], "fee": 0, "hours": 2, "area": "Old City"},
            {"name": "Albert Hall Museum", "tags": ["history", "museum"], "fee": 40, "hours": 1.5, "area": "Ram Niwas Garden"},
            {"name": "Patrika Gate", "tags": ["photography", "architecture"], "fee": 0, "hours": 1, "area": "Jawahar Circle"},
            {"name": "Galtaji (Monkey Temple)", "tags": ["spiritual", "nature"], "fee": 0, "hours": 1.5, "area": "East Jaipur"},
            {"name": "Chokhi Dhani cultural village", "tags": ["culture", "food"], "fee": 1100, "hours": 3.5, "area": "Tonk Road"},
        ],
        "food": [
            {"dish": "Pyaaz kachori", "where": "Rawat Mishthan Bhandar", "cost": 60},
            {"dish": "Lassi", "where": "Lassiwala, MI Road", "cost": 80},
            {"dish": "Dal baati churma", "where": "Laxmi Mishthan Bhandar (LMB), Johari Bazaar", "cost": 450},
            {"dish": "Laal maas", "where": "Handi Restaurant, MI Road", "cost": 550},
            {"dish": "Ghewar & mawa kachori", "where": "Sampat / LMB", "cost": 120},
            {"dish": "Rajasthani thali", "where": "Chokhi Dhani or Spice Court", "cost": 700},
        ],
    },
    "udaipur": {
        "state": "Rajasthan",
        "best_time": "September to March",
        "getting_around": "Walkable old city; autos for longer hops.",
        "cost_multiplier": 1.1,
        "tip": "Sunset boat rides on Lake Pichola sell out on weekends; book before 3 pm.",
        "places": [
            {"name": "City Palace Udaipur", "tags": ["history", "architecture", "museum"], "fee": 300, "hours": 3, "area": "Lake Pichola"},
            {"name": "Lake Pichola boat ride", "tags": ["views", "romance"], "fee": 500, "hours": 1, "area": "Lake Pichola"},
            {"name": "Jagdish Temple", "tags": ["spiritual", "history"], "fee": 0, "hours": 0.5, "area": "Old City"},
            {"name": "Bagore ki Haveli dance show", "tags": ["culture", "history"], "fee": 150, "hours": 1.5, "area": "Gangaur Ghat"},
            {"name": "Sajjangarh (Monsoon Palace)", "tags": ["history", "views"], "fee": 155, "hours": 2, "area": "West Udaipur"},
            {"name": "Saheliyon ki Bari", "tags": ["nature", "history"], "fee": 50, "hours": 1, "area": "North Udaipur"},
            {"name": "Fateh Sagar Lake", "tags": ["nature", "views", "food"], "fee": 0, "hours": 1.5, "area": "North Udaipur"},
            {"name": "Hathi Pol Bazaar", "tags": ["shopping"], "fee": 0, "hours": 1.5, "area": "Old City"},
        ],
        "food": [
            {"dish": "Dal baati churma", "where": "Natraj Dining Hall", "cost": 300},
            {"dish": "Kachori & mirchi vada", "where": "Jagdish Mishthan Bhandar", "cost": 60},
            {"dish": "Rooftop dinner with lake view", "where": "Ambrai / Upre", "cost": 1500},
            {"dish": "Corn pakoras & coffee", "where": "Fateh Sagar stalls", "cost": 100},
        ],
    },
    "goa": {
        "state": "Goa",
        "best_time": "November to February",
        "getting_around": "Rent a scooter (₹400–500/day) or use GoaMiles cabs.",
        "cost_multiplier": 1.25,
        "tip": "Stay in one zone (North or South); travel between them eats half a day.",
        "places": [
            {"name": "Basilica of Bom Jesus", "tags": ["history", "architecture", "spiritual"], "fee": 0, "hours": 1, "area": "Old Goa"},
            {"name": "Se Cathedral", "tags": ["history", "architecture"], "fee": 0, "hours": 0.5, "area": "Old Goa"},
            {"name": "Fontainhas Latin Quarter walk", "tags": ["history", "culture", "photography"], "fee": 0, "hours": 2, "area": "Panaji"},
            {"name": "Fort Aguada", "tags": ["history", "views"], "fee": 25, "hours": 1, "area": "North Goa"},
            {"name": "Chapora Fort", "tags": ["history", "views"], "fee": 0, "hours": 1, "area": "North Goa"},
            {"name": "Anjuna Wednesday flea market", "tags": ["shopping", "food"], "fee": 0, "hours": 2, "area": "North Goa"},
            {"name": "Palolem Beach", "tags": ["beach", "nature"], "fee": 0, "hours": 4, "area": "South Goa"},
            {"name": "Baga & Calangute beaches", "tags": ["beach", "nightlife"], "fee": 0, "hours": 3, "area": "North Goa"},
            {"name": "Spice plantation tour", "tags": ["nature", "food"], "fee": 600, "hours": 3, "area": "Ponda"},
        ],
        "food": [
            {"dish": "Fish curry rice", "where": "Ritz Classic, Panaji", "cost": 450},
            {"dish": "Pork vindaloo & sorpotel", "where": "Viva Panjim", "cost": 500},
            {"dish": "Bebinca", "where": "any Panaji bakery", "cost": 100},
            {"dish": "Beach shack seafood", "where": "Anjuna / Palolem shacks", "cost": 800},
        ],
    },
    "varanasi": {
        "state": "Uttar Pradesh",
        "best_time": "October to March",
        "getting_around": "Walk the ghats; e-rickshaws and boats for the rest.",
        "cost_multiplier": 0.85,
        "tip": "Watch the Ganga Aarti from a boat at Dashashwamedh Ghat; agree the boat fare before boarding.",
        "places": [
            {"name": "Dashashwamedh Ghat Ganga Aarti", "tags": ["spiritual", "culture"], "fee": 0, "hours": 1.5, "area": "Ghats"},
            {"name": "Sunrise boat ride", "tags": ["spiritual", "views"], "fee": 400, "hours": 1.5, "area": "Ghats"},
            {"name": "Kashi Vishwanath Temple", "tags": ["spiritual", "history"], "fee": 0, "hours": 2, "area": "Old City"},
            {"name": "Sarnath", "tags": ["history", "spiritual", "museum"], "fee": 25, "hours": 3, "area": "Sarnath"},
            {"name": "Ramnagar Fort", "tags": ["history", "museum"], "fee": 75, "hours": 1.5, "area": "Across the river"},
            {"name": "Banaras Hindu University & Bharat Kala Bhavan", "tags": ["history", "museum"], "fee": 50, "hours": 2, "area": "Lanka"},
            {"name": "Old city lanes food walk", "tags": ["food", "culture"], "fee": 0, "hours": 2, "area": "Old City"},
        ],
        "food": [
            {"dish": "Kachori sabzi & jalebi", "where": "Ram Bhandar, Thatheri Bazaar", "cost": 80},
            {"dish": "Banarasi paan", "where": "Keshav Paan Bhandar", "cost": 50},
            {"dish": "Malaiyyo (winter only)", "where": "Chowk lanes", "cost": 60},
            {"dish": "Tamatar chaat", "where": "Kashi Chat Bhandar", "cost": 80},
            {"dish": "Blue Lassi", "where": "Blue Lassi Shop", "cost": 120},
        ],
    },
    "delhi": {
        "state": "Delhi",
        "best_time": "October to March",
        "getting_around": "Delhi Metro covers almost everything (₹30–60 per ride).",
        "cost_multiplier": 1.15,
        "tip": "Most monuments are closed one day a week (Red Fort: Monday); check before planning.",
        "places": [
            {"name": "Red Fort", "tags": ["history", "architecture"], "fee": 80, "hours": 2, "area": "Old Delhi"},
            {"name": "Jama Masjid", "tags": ["history", "spiritual"], "fee": 0, "hours": 1, "area": "Old Delhi"},
            {"name": "Chandni Chowk food walk", "tags": ["food", "shopping"], "fee": 0, "hours": 2.5, "area": "Old Delhi"},
            {"name": "Humayun's Tomb", "tags": ["history", "architecture"], "fee": 40, "hours": 1.5, "area": "Nizamuddin"},
            {"name": "Qutub Minar", "tags": ["history", "architecture"], "fee": 40, "hours": 1.5, "area": "Mehrauli"},
            {"name": "India Gate & Kartavya Path", "tags": ["history", "views"], "fee": 0, "hours": 1, "area": "Central Delhi"},
            {"name": "National Museum", "tags": ["history", "museum"], "fee": 20, "hours": 2.5, "area": "Central Delhi"},
            {"name": "Lodhi Garden", "tags": ["nature", "history"], "fee": 0, "hours": 1, "area": "Lodhi Road"},
            {"name": "Hauz Khas Village", "tags": ["food", "nightlife", "history"], "fee": 0, "hours": 2, "area": "South Delhi"},
        ],
        "food": [
            {"dish": "Parathas", "where": "Paranthe Wali Gali, Chandni Chowk", "cost": 200},
            {"dish": "Butter chicken", "where": "Moti Mahal, Daryaganj", "cost": 650},
            {"dish": "Kebabs & nihari", "where": "Karim's, near Jama Masjid", "cost": 450},
            {"dish": "Chole bhature", "where": "Sita Ram Diwan Chand, Paharganj", "cost": 150},
            {"dish": "Daulat ki chaat (winter)", "where": "Chandni Chowk", "cost": 80},
        ],
    },
    "agra": {
        "state": "Uttar Pradesh",
        "best_time": "October to March",
        "getting_around": "Autos or a day cab (~₹1,800); Taj area has battery buses.",
        "cost_multiplier": 0.95,
        "tip": "The Taj Mahal is closed on Fridays; go at sunrise to avoid crowds.",
        "places": [
            {"name": "Taj Mahal (sunrise)", "tags": ["history", "architecture"], "fee": 250, "hours": 3, "area": "Taj Ganj"},
            {"name": "Agra Fort", "tags": ["history", "architecture"], "fee": 50, "hours": 2, "area": "Agra Fort"},
            {"name": "Itimad-ud-Daulah (Baby Taj)", "tags": ["history", "architecture"], "fee": 30, "hours": 1, "area": "Yamuna east bank"},
            {"name": "Mehtab Bagh (Taj sunset view)", "tags": ["views", "nature"], "fee": 30, "hours": 1, "area": "Yamuna east bank"},
            {"name": "Fatehpur Sikri", "tags": ["history", "architecture"], "fee": 50, "hours": 3, "area": "40 km west"},
            {"name": "Kinari Bazaar", "tags": ["shopping", "food"], "fee": 0, "hours": 1.5, "area": "Old Agra"},
        ],
        "food": [
            {"dish": "Bedai & jalebi breakfast", "where": "Deviram Sweets", "cost": 80},
            {"dish": "Petha", "where": "Panchhi Petha", "cost": 150},
            {"dish": "Mughlai thali", "where": "Pinch of Spice", "cost": 700},
        ],
    },
}


def _normalize_city(city: str) -> str:
    return city.strip().lower().split(",")[0].strip()


# Map free-form interest words from the user onto the tags used in DESTINATIONS.
INTEREST_SYNONYMS = {
    "beaches": "beach", "sea": "beach", "seafood": "food", "local food": "food",
    "cuisine": "food", "street food": "food", "foodie": "food", "historical": "history",
    "heritage": "history", "forts": "history", "palaces": "history", "portuguese": "history",
    "temples": "spiritual", "religious": "spiritual", "museums": "museum", "markets": "shopping",
    "parties": "nightlife", "party": "nightlife", "lakes": "views", "sunset": "views",
    "photos": "photography", "art": "culture", "nature walks": "nature",
}


def _normalize_interest(interest: str) -> str:
    word = interest.strip().lower()
    return INTEREST_SYNONYMS.get(word, word)


def get_destination_info(city: str) -> dict:
    """Returns practical information about a destination city in India.

    Use this first to learn about the destination: when to visit, how to get
    around, a local tip, the full list of attractions, and signature local food.

    Args:
        city: Name of the destination city, e.g. "Jaipur".

    Returns:
        A dict with status "success" and the destination details, or status
        "not_found" with the list of cities that have curated data.
    """
    data = DESTINATIONS.get(_normalize_city(city))
    if not data:
        return {
            "status": "not_found",
            "message": f"No curated data for '{city}'. Use general knowledge and tell the user the details are unverified.",
            "supported_cities": sorted(c.title() for c in DESTINATIONS),
        }
    return {"status": "success", "city": city.title(), **data}


def recommend_places(city: str, interests: list[str]) -> dict:
    """Ranks a city's attractions and food spots by how well they match the traveller's interests.

    Args:
        city: Name of the destination city, e.g. "Jaipur".
        interests: Interest keywords from the user's request, e.g.
            ["history", "food"]. Useful tags include history, architecture,
            food, shopping, spiritual, nature, beach, culture, views,
            museum, nightlife, photography.

    Returns:
        A dict with places sorted best-match first (each with the matching
        tags, entry fee in INR, hours needed and area) plus food picks.
    """
    data = DESTINATIONS.get(_normalize_city(city))
    if not data:
        return {"status": "not_found", "supported_cities": sorted(c.title() for c in DESTINATIONS)}

    wanted = {_normalize_interest(i) for i in interests}
    ranked = []
    for place in data["places"]:
        matches = sorted(wanted.intersection(place["tags"]))
        ranked.append({**place, "matches": matches, "score": len(matches)})
    ranked.sort(key=lambda p: (-p["score"], p["area"]))

    return {
        "status": "success",
        "city": city.title(),
        "interests": sorted(wanted),
        "top_matches": [p for p in ranked if p["score"] > 0],
        "other_places": [p for p in ranked if p["score"] == 0],
        "food_picks": data["food"],
        "local_tip": data["tip"],
    }


def _cost_for_level(level, days, nights, travelers, rooms, multiplier, entry_per_person):
    rates = COMFORT_LEVELS[level]
    stay = round(rates["stay"] * multiplier) * nights * rooms
    food = round(rates["food"] * multiplier) * days * travelers
    transport = round(rates["transport"] * multiplier) * days * travelers
    entry = entry_per_person * travelers
    subtotal = stay + food + transport + entry
    buffer = round(subtotal * 0.10)
    breakdown = {
        "accommodation": stay,
        "food": food,
        "local_transport": transport,
        "entry_fees": entry,
        "buffer_10_percent": buffer,
    }
    return breakdown, subtotal + buffer


def estimate_budget(
    city: str,
    days: int,
    travelers: int = 1,
    total_budget_inr: int = 0,
    planned_entry_fees_inr: int = 0,
    comfort_level: str = "auto",
) -> dict:
    """Estimates the trip cost in INR and checks it against the user's budget.

    Excludes travel to and from the city; covers stay, food, local transport,
    entry fees and a 10% buffer. With comfort_level "auto" it picks the most
    comfortable level (premium, mid, budget) that fits the user's budget.

    Args:
        city: Destination city, e.g. "Jaipur".
        days: Number of days of the trip (nights = days - 1, minimum 1).
        travelers: Number of people travelling. Two travellers share a room.
        total_budget_inr: The user's total budget in INR, or 0 if not given.
        planned_entry_fees_inr: Sum of per-person entry fees for the places in
            the itinerary.
        comfort_level: "auto" (default) unless the user explicitly asked for
            "budget", "mid" or "premium".

    Returns:
        A dict with the chosen comfort level, the cost breakdown, total,
        per-person cost, whether it fits the budget (and by how much), and
        the total for every comfort level for comparison.
    """
    level = comfort_level.strip().lower()
    if level != "auto" and level not in COMFORT_LEVELS:
        return {"status": "error", "message": f"comfort_level must be auto or one of {list(COMFORT_LEVELS)}"}
    days = max(1, int(days))
    travelers = max(1, int(travelers))
    nights = max(1, days - 1)
    rooms = (travelers + 1) // 2
    budget = int(total_budget_inr)

    data = DESTINATIONS.get(_normalize_city(city))
    multiplier = data["cost_multiplier"] if data else 1.0
    costs = {
        lvl: _cost_for_level(lvl, days, nights, travelers, rooms, multiplier, int(planned_entry_fees_inr))
        for lvl in COMFORT_LEVELS
    }

    if level == "auto":
        if not budget:
            level = "mid"
        else:
            fitting = [lvl for lvl in ("premium", "mid", "budget") if costs[lvl][1] <= budget]
            level = fitting[0] if fitting else "budget"

    breakdown, total = costs[level]
    result = {
        "status": "success",
        "city": city.title(),
        "comfort_level": level,
        "days": days,
        "nights": nights,
        "travelers": travelers,
        "rooms": rooms,
        "breakdown_inr": breakdown,
        "total_inr": total,
        "per_person_inr": round(total / travelers),
        "total_by_comfort_level_inr": {lvl: c[1] for lvl, c in costs.items()},
        "note": "Excludes travel to/from the city." + ("" if data else " City not in curated data; rates are national averages."),
    }
    if budget:
        diff = budget - total
        result["user_budget_inr"] = budget
        result["within_budget"] = diff >= 0
        result["remaining_inr" if diff >= 0 else "over_budget_by_inr"] = abs(diff)
    return result


# WMO weather codes used by Open-Meteo, grouped into plain descriptions.
_WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "fog", 51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain", 80: "rain showers",
    81: "heavy rain showers", 82: "violent rain showers", 95: "thunderstorm",
    96: "thunderstorm with hail", 99: "thunderstorm with hail",
}
_FORECAST_HORIZON_DAYS = 16


def _get_json(url: str, params: dict) -> dict:
    with urllib.request.urlopen(f"{url}?{urllib.parse.urlencode(params)}", timeout=10) as resp:
        return json.load(resp)


def get_weather_forecast(city: str, start_date: str = "", days: int = 3) -> dict:
    """Gets the live daily weather forecast for a city in India.

    Forecasts are only available up to 16 days ahead. Use this when the user
    gives travel dates or is travelling soon, and adapt the plan to the weather.

    Args:
        city: City name, e.g. "Jaipur".
        start_date: First day of the trip as YYYY-MM-DD. Empty means today.
        days: Number of days to forecast.

    Returns:
        A dict with one entry per day (date, condition, min/max °C, chance of
        rain), or status "too_far_ahead" / "error" with a message.
    """
    today = datetime.date.today()
    try:
        start = datetime.date.fromisoformat(start_date) if start_date else today
    except ValueError:
        return {"status": "error", "message": "start_date must be YYYY-MM-DD"}
    start = max(start, today)
    end = min(start + datetime.timedelta(days=max(1, int(days)) - 1),
              today + datetime.timedelta(days=_FORECAST_HORIZON_DAYS - 1))
    if start > end:
        return {
            "status": "too_far_ahead",
            "message": f"Forecasts only cover the next {_FORECAST_HORIZON_DAYS} days. "
                       "Use the destination's best time to visit instead.",
        }

    try:
        geo = _get_json("https://geocoding-api.open-meteo.com/v1/search",
                        {"name": _normalize_city(city), "count": 1, "countryCode": "IN"})
        if not geo.get("results"):
            return {"status": "error", "message": f"Could not find '{city}' in India."}
        place = geo["results"][0]
        forecast = _get_json("https://api.open-meteo.com/v1/forecast", {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "Asia/Kolkata",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        })
    except OSError as e:
        return {"status": "error", "message": f"Weather service unavailable: {e}"}

    daily = forecast["daily"]
    return {
        "status": "success",
        "city": place["name"],
        "source": "Open-Meteo (live forecast)",
        "days": [
            {
                "date": date,
                "condition": _WEATHER_CODES.get(code, f"weather code {code}"),
                "min_c": tmin,
                "max_c": tmax,
                "rain_chance_percent": rain,
            }
            for date, code, tmin, tmax, rain in zip(
                daily["time"], daily["weather_code"], daily["temperature_2m_min"],
                daily["temperature_2m_max"], daily["precipitation_probability_max"])
        ],
    }


def _gemini() -> Gemini:
    # Gemini occasionally returns 503 "high demand"; retry a few times with backoff.
    # 429 (quota) is not retried: every retry would count against the quota.
    return Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(
            attempts=3, initial_delay=2, max_delay=20, http_status_codes=[500, 502, 503, 504]
        ),
    )


def _tool_error_to_result(tool, args, tool_context, error: Exception) -> dict:
    """Turns a failing tool (e.g. the weather service being down) into a normal
    tool result, so the planner can carry on instead of the whole request failing."""
    return {
        "status": "error",
        "tool": tool.name,
        "message": f"{type(error).__name__}: {str(error)[:200]}",
        "instruction": "Continue without this tool. Use your general knowledge and label those details as approximate.",
    }


root_agent = Agent(
    name="travel_planner",
    model=_gemini(),
    description="Plans day-wise trips in India with place recommendations and a budget estimate.",
    instruction="""
You are a friendly, practical personal travel planner focused on India.

When the user sends a travel request, work through these steps:

1. **Understand the request.** Extract destination, number of days, number of
   travellers (default 1), total budget in INR, interests, and any preferences
   (pace, food habits, comfort). If the destination is missing, ask one short
   question for it and stop. For anything else that is missing, make a
   sensible assumption (e.g. 3 days, interests implied by who is travelling)
   and state it under "Assumptions".

2. **Research.** Call `get_destination_info` and then `recommend_places` with
   the user's interests. If the city is not supported, plan from your own
   knowledge and clearly label costs and details as approximate.
   If the user gave travel dates, or the trip is within the next 2 weeks,
   call `get_weather_forecast` and adapt the plan: indoor places on rainy or
   very hot afternoons, early starts on hot days.

3. **Build the itinerary.** Group places that are in the same `area` on the
   same day to minimise travel. Keep each day realistic (about 6–8 hours of
   sightseeing, using the `hours` field). Put the strongest interest matches
   first. Weave in the recommended local food for breakfast, lunch, snacks and
   dinner.

4. **Estimate the budget.** Add up the per-person entry fees of the places you
   chose and call `estimate_budget` once. Leave `comfort_level` as "auto"
   unless the user asked for a specific level; the tool picks the best level
   that fits the budget. Describe the stay using the `comfort_level` the tool
   returned. If `within_budget` is false, say so and suggest cuts. Never
   invent totals — use the tool's numbers.

5. **Reply in this format** (Markdown, concise):

   ### Trip summary
   One line each: destination, duration, travellers, budget, interests, and
   any assumptions you made.

   ### Recommended places
   A bulleted list of the top places with one line on why each fits the
   user's interests.

   ### Day-wise itinerary
   For each day: a `#### Day N – <theme>` heading, then Morning / Afternoon /
   Evening bullets naming the places and where to eat.

   ### Budget estimate
   A Markdown table of the breakdown from `estimate_budget` (category, amount
   in ₹), with the total, and a line saying whether it fits the budget and by
   how much.

   ### Tips
   2–3 short practical tips, including the local tip from the tools and, if
   you fetched it, a one-line weather summary with what to pack.

For follow-up messages (e.g. "make day 2 more relaxed", "we are now 2
people"), update only what changed, re-run `estimate_budget` if costs change,
and show the revised parts.
""",
    tools=[
        get_destination_info,
        recommend_places,
        estimate_budget,
        get_weather_forecast,
    ],
    on_tool_error_callback=_tool_error_to_result,
)
