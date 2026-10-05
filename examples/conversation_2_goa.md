# Example 2 — Goa, couple, beaches + Portuguese history + seafood

A 4-day trip for 2 with ₹30,000. `estimate_budget` (comfort_level=auto) finds that mid-range would cost more than the budget, so it picks the budget tier, and the agent plans the stay accordingly.

*Recorded in the ADK Web UI (`adk web`) with `gemini-3.5-flash-lite` on 2026-10-05. Tool calls are shown as they happened. Screenshots: `screenshots/05–06_*.jpg`.*

---

## 🧑 User

Plan a 4-day Goa trip for me and my wife. Budget ₹30,000. We love beaches, Portuguese history and seafood.

> 🔧 **Tool call:** `get_destination_info({"city": "Goa"})`

> 🔧 **Tool call:** `recommend_places({"interests": ["beaches", "history", "portuguese", "seafood"], "city": "Goa"})`

> 🔧 **Tool call:** `estimate_budget({"comfort_level": "auto", "city": "Goa", "total_budget_inr": 30000, "days": 4, "planned_entry_fees_inr": 50, "travelers": 2})`

## 🤖 Travel Planner Agent

### Trip summary
- **Destination:** Goa
- **Duration:** 4 days (3 nights)
- **Travellers:** 2 people (you and your wife)
- **Total Budget:** ₹30,000
- **Interests:** Beaches, Portuguese history, seafood
- **Assumptions:** You will stay in a budget beach resort or guesthouse in North/Central Goa, rent a scooter for local exploration, and flights/trains to Goa are booked separately.

### Recommended places
- **Fontainhas Latin Quarter walk:** Stunning colorful Portuguese colonial homes and narrow winding lanes, perfect for history and photography.
- **Basilica of Bom Jesus & Se Cathedral:** UNESCO World Heritage sites showcasing magnificent 16th-century Portuguese architecture and history.
- **Fort Aguada & Chapora Fort:** Historic coastal forts offering panoramic views of the Arabian Sea.
- **Palolem & Anjuna Beaches:** Scenic stretches for relaxing by the waves and enjoying beachside seafood shacks.

### Day-wise itinerary
#### Day 1 – Portuguese Heritage & Old Goa
- **Morning:** Arrive in Goa, check into your stay, and head to **Old Goa** to explore the magnificent **Basilica of Bom Jesus** and the grand **Se Cathedral**.
- **Afternoon:** Enjoy authentic Goan seafood lunch at *Ritz Classic, Panaji* (try their signature fish curry rice).
- **Evening:** Wander through **Fontainhas Latin Quarter**, admiring the vibrant Portuguese-style villas, and stop by a local bakery for some *Bebinca*.

#### Day 2 – Historic Forts & North Goa Beaches
- **Morning:** Visit **Fort Aguada** for sweeping sea views and a glimpse of colonial military history.
- **Afternoon:** Head to a beachside shack in Anjuna or Calangute for fresh grilled fish and a relaxed lunch by the shore.
- **Evening:** Climb up to **Chapora Fort** just in time for a breathtaking sunset over the Arabian Sea, followed by dinner nearby.

#### Day 3 – South Goa Coastal Retreat
- **Morning:** Travel down to South Goa and spend the morning relaxing on the pristine, palm-fringed sands of **Palolem Beach**.
- **Afternoon:** Enjoy a leisurely seaside lunch featuring local catch of the day at a Palolem beach shack.
- **Evening:** Take a gentle boat ride or stroll along the quiet shores before heading back north for a cozy dinner.

#### Day 4 – Markets & Souvenir Shopping
- **Morning:** Explore local markets for spices, cashews, and Goan handicrafts.
- **Afternoon:** Savor a final traditional Goan meal featuring pork vindaloo or fish curry.
- **Evening:** Sunset stroll along the beach, pick up local sweets, and depart for your journey home.

### Budget estimate

| Category | Amount in ₹ |
| --- | --- |
| Accommodation (3 nights) | ₹4,500 |
| Food & Seafood | ₹6,000 |
| Local Transport (Scooter rental & fuel/cabs) | ₹4,000 |
| Entry Fees | ₹100 |
| 10% Buffer | ₹1,460 |
| **Total Estimated Cost** | **₹16,060** |

*Great news! Your estimated trip cost of ₹16,060 is well within your ₹30,000 budget, leaving you ₹13,940 to spare for extra leisure activities, shopping, or upgrades.*

### Tips
- **Stay in one zone (North or South); travel between them eats half a day.**
- Renting a scooter is the most budget-friendly and fun way to explore the coastal roads.
- Always check seafood prices by weight at beach shacks before placing your order to avoid surprises.

