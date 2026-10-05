# Example 1 — Jaipur, solo, history & food (+ follow-up)

The assignment's sample request. The agent researches the city, ranks places by interest, builds a 3-day plan and checks it against ₹15,000. A follow-up changes the group to 2 people and asks for a lighter Day 3; the agent re-runs the budget tool and revises the plan.

*Recorded in the ADK Web UI (`adk web`) with `gemini-3.5-flash-lite` on 2026-10-05. Tool calls are shown as they happened. Screenshots: `screenshots/01–04_*.jpg`.*

---

## 🧑 User

I want to visit Jaipur for 3 days with a budget of ₹15,000. I like history and local food.

> 🔧 **Tool call:** `get_destination_info({"city": "Jaipur"})`

> 🔧 **Tool call:** `recommend_places({"city": "Jaipur", "interests": ["history", "food"]})`

> 🔧 **Tool call:** `estimate_budget({"total_budget_inr": 15000, "city": "Jaipur", "comfort_level": "mid", "planned_entry_fees_inr": 690, "travelers": 1, "days": 3})`

## 🤖 Travel Planner Agent

### Trip summary
* **Destination:** Jaipur
* **Duration:** 3 days / 2 nights
* **Travellers:** 1 (solo)
* **Budget:** ₹15,000
* **Interests:** History and local food
* **Assumptions:** Solo budget/mid-range comfort, starting and ending in Jaipur (travel to/from Jaipur excluded).

### Recommended places
* **Amber Fort:** Majestic hilltop Rajput fortress with stunning palaces and mirror work.
* **Jaigarh Fort:** Historic stronghold housing the world's largest cannon on wheels.
* **Nahargarh Fort:** Hilltop fort offering panoramic sunset views over Jaipur.
* **City Palace:** Opulent royal residence blending Rajasthani and Mughal architecture.
* **Jantar Mantar:** 18th-century astronomical observatory and UNESCO World Heritage site.
* **Hawa Mahal:** Iconic "Palace of Winds" with its intricate honeycombed facade.
* **Albert Hall Museum:** Rajasthan's oldest museum with a rich historical collection.
* **Johari & Bapu Bazaar:** Vibrant traditional markets famous for local food and crafts.

### Day-wise itinerary

#### Day 1 – Majestic Amer & Sunset Views
* **Morning:** Explore the grand **Amber Fort** and nearby **Panna Meena ka Kund** stepwell. Grab breakfast with a *Pyaaz kachori* at Rawat Mishthan Bhandar.
* **Afternoon:** Visit the mighty **Jaigarh Fort** for history and weaponry exhibits. Enjoy lunch with a *Rajasthani thali* at Spice Court.
* **Evening:** Head up to **Nahargarh Fort** for a breathtaking sunset over the Pink City. End the day with famous *Laal maas* at Handi Restaurant on MI Road.

#### Day 2 – Heart of the Pink City
* **Morning:** Start with a refreshing morning *Lassi* at Lassiwala (MI Road), then explore the intricate **Hawa Mahal** and the astronomical wonders of **Jantar Mantar**.
* **Afternoon:** Tour the royal **City Palace** and its museum. Stop for lunch and try *Dal baati churma* at Laxmi Mishthan Bhandar (LMB) in Johari Bazaar.
* **Evening:** Wander through **Johari & Bapu Bazaar** for food snacks and shopping, and treat yourself to local *Ghewar*.

#### Day 3 – Museums & Heritage
* **Morning:** Visit the stunning **Albert Hall Museum** at Ram Niwas Garden.
* **Afternoon:** Explore the historic **Galtaji (Monkey Temple)** complex tucked away in the hills. Enjoy a leisurely lunch in the city.
* **Evening:** Wrap up your trip with a stroll around **Patrika Gate** for great photography before departure.

### Budget estimate

| Category | Amount (in ₹) |
| :--- | :--- |
| Accommodation (2 nights) | ₹5,600 |
| Food | ₹3,300 |
| Local Transport | ₹2,400 |
| Entry Fees | ₹690 |
| 10% Buffer | ₹1,199 |
| **Total** | **₹13,189** |

* **Fits budget:** Yes, within your ₹15,000 budget with ₹1,811 to spare.

### Tips
* **Local tip:** Buy the composite ticket (₹300 for Indians) covering Amber, Nahargarh, Hawa Mahal, Jantar Mantar and Albert Hall to save money and time.
* **Getting around:** Use auto-rickshaws or ride-hailing apps (Ola/Uber) for local travel, or hire a cab for the day.
* **Best time:** Wear comfortable walking shoes as forts and palaces involve plenty of stone stairs and walking.

## 🧑 User

My friend is joining me now, so we are 2 people with a total budget of ₹25,000. Also make Day 3 more relaxed.

> 🔧 **Tool call:** `estimate_budget({"total_budget_inr": 25000, "comfort_level": "mid", "travelers": 2, "days": 3, "city": "Jaipur", "planned_entry_fees_inr": 690})`

## 🤖 Travel Planner Agent

### Trip summary
* **Destination:** Jaipur
* **Duration:** 3 days / 2 nights
* **Travellers:** 2
* **Budget:** ₹25,000
* **Interests:** History and local food
* **Assumptions:** 2 travelers sharing 1 room (mid-range comfort), starting and ending in Jaipur.

### Recommended places
* **Amber Fort:** Majestic hilltop Rajput fortress with stunning palaces and mirror work.
* **Jaigarh Fort:** Historic stronghold housing the world's largest cannon on wheels.
* **Nahargarh Fort:** Hilltop fort offering panoramic sunset views over Jaipur.
* **City Palace:** Opulent royal residence blending Rajasthani and Mughal architecture.
* **Jantar Mantar:** 18th-century astronomical observatory and UNESCO World Heritage site.
* **Hawa Mahal:** Iconic "Palace of Winds" with its intricate honeycombed facade.
* **Albert Hall Museum:** Rajasthan's oldest museum with a rich historical collection.
* **Johari & Bapu Bazaar:** Vibrant traditional markets famous for local food and crafts.

### Day-wise itinerary

#### Day 1 – Majestic Amer & Sunset Views
* **Morning:** Explore the grand **Amber Fort** and nearby **Panna Meena ka Kund** stepwell. Grab breakfast with a *Pyaaz kachori* at Rawat Mishthan Bhandar.
* **Afternoon:** Visit the mighty **Jaigarh Fort** for history and weaponry exhibits. Enjoy lunch with a *Rajasthani thali* at Spice Court.
* **Evening:** Head up to **Nahargarh Fort** for a breathtaking sunset over the Pink City. End the day with famous *Laal maas* at Handi Restaurant on MI Road.

#### Day 2 – Heart of the Pink City
* **Morning:** Start with a refreshing morning *Lassi* at Lassiwala (MI Road), then explore the intricate **Hawa Mahal** and the astronomical wonders of **Jantar Mantar**.
* **Afternoon:** Tour the royal **City Palace** and its museum. Stop for lunch and try *Dal baati churma* at Laxmi Mishthan Bhandar (LMB) in Johari Bazaar.
* **Evening:** Wander through **Johari & Bapu Bazaar** for food snacks and shopping, and treat yourself to local *Ghewar*.

#### Day 3 – Relaxed Heritage & Museums *(Updated)*
* **Morning:** Enjoy a relaxed breakfast, then take a leisurely stroll through the pleasant gardens and galleries of the **Albert Hall Museum**.
* **Afternoon:** Have a nice, unhurried lunch in the city centre and stop by **Patrika Gate** for photos and a relaxed walk.
* **Evening:** Spend a calm evening shopping or sampling more local sweets before heading home.

### Budget estimate

| Category | Amount (in ₹) |
| :--- | :--- |
| Accommodation (2 nights, 1 room) | ₹5,600 |
| Food | ₹6,600 |
| Local Transport | ₹4,800 |
| Entry Fees (2 pax) | ₹1,380 |
| 10% Buffer | ₹1,838 |
| **Total** | **₹20,218** |

* **Fits budget:** Yes, well within your ₹25,000 budget with ₹4,782 to spare (approx. ₹10,109 per person).

### Tips
* **Local tip:** Buy the composite ticket (₹300 per person for Indians) covering Amber, Nahargarh, Hawa Mahal, Jantar Mantar and Albert Hall to save money and time.
* **Getting around:** Sharing an auto-rickshaw or booking a cab together makes local transit even more cost-effective.
* **Best time:** Wear comfortable walking shoes as forts and palaces involve plenty of stone stairs and walking.

