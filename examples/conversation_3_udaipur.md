# Example 3 — Udaipur with parents, number of days not given

An incomplete request: no trip length and no interests. The agent assumes 3 days, infers family-friendly interests, says so under *Assumptions*, and plans for 3 travellers in 2 rooms, keeping within ₹40,000.

*Recorded in the ADK Web UI (`adk web`) with `gemini-3.5-flash-lite` on 2026-10-05. Tool calls are shown as they happened. Screenshots: `screenshots/07–08_*.jpg`.*

---

## 🧑 User

Help me plan a trip to Udaipur with my parents. Our budget is around ₹40,000.

> 🔧 **Tool call:** `get_destination_info({"city": "Udaipur"})`

> 🔧 **Tool call:** `recommend_places({"city": "Udaipur", "interests": ["history", "architecture", "culture", "views", "spiritual"]})`

> 🔧 **Tool call:** `estimate_budget({"city": "Udaipur", "total_budget_inr": 40000, "comfort_level": "auto", "travelers": 3, "days": 3, "planned_entry_fees_inr": 1155})`

## 🤖 Travel Planner Agent

### Trip summary
* Destination: Udaipur
* Duration: 3 days (2 nights)
* Travellers: 3 adults (travelling with parents)
* Budget: ₹40,000 total
* Interests: History, architecture, culture, views, spiritual
* Assumptions: 3 days planned as a comfortable pace for parents, staying in 2 mid-range comfortable rooms.

### Recommended places
* **City Palace Udaipur**: A magnificent palace complex showcasing rich Mewar history and architecture.
* **Lake Pichola boat ride**: Offers breathtaking views of the lake palaces and the Aravalli hills.
* **Jagdish Temple**: A beautiful 17th-century shrine showcasing intricate Indo-Aryan architecture.
* **Bagore ki Haveli dance show**: A vibrant cultural spectacle right by the lake showcasing traditional Rajasthani folk dances.
* **Sajjangarh (Monsoon Palace)**: Perched high on a hill, offering panoramic sunset views over Udaipur's lakes.
* **Saheliyon ki Bari & Fateh Sagar Lake**: Beautiful historic gardens and a scenic lakeside stroll.

### Day-wise itinerary
#### Day 1 – Royal Heritage of the Old City
* **Morning**: Start with authentic kachoris and mirchi vada at *Jagdish Mishthan Bhandar*, then walk over to explore the stunning **Jagdish Temple**.
* **Afternoon**: Spend a few hours exploring the grand halls and museums of the **City Palace Udaipur**. Enjoy a traditional thali lunch at *Natraj Dining Hall*.
* **Evening**: Take a serene **Lake Pichola boat ride** just before sunset, followed by the cultural **Bagore ki Haveli dance show** at Gangaur Ghat. Wrap up with a lakeside dinner at *Ambrai*.

#### Day 2 – Lakes and Gardens of North Udaipur
* **Morning**: Stroll through the fountains and lotus pools of **Saheliyon ki Bari**. Grab morning tea and corn pakoras by **Fateh Sagar Lake**.
* **Afternoon**: Enjoy a relaxed boat or lakeside lunch nearby, and pick up some local crafts and textiles at **Hathi Pol Bazaar**.
* **Evening**: Take an auto up to **Sajjangarh (Monsoon Palace)** for sweeping sunset views of the city and lakes, followed by a cozy dinner in town.

#### Day 3 – Temples, Views & Departure
* **Morning**: Revisit any favorite spots in the walkable old city or pick up souvenirs before checking out.
* **Afternoon**: Enjoy a final leisurely lunch by the water before heading onward.

### Budget estimate

| Category | Amount in ₹ |
| :--- | :--- |
| Accommodation | ₹12,320 |
| Food | ₹10,890 |
| Local Transport | ₹7,920 |
| Entry Fees | ₹3,465 |
| Buffer (10%) | ₹3,460 |
| **Total** | **₹38,055** |

*This fits your budget of ₹40,000 and leaves ₹1,945 to spare.*

### Tips
* Sunset boat rides on Lake Pichola sell out on weekends; book before 3 pm.
* Hire auto-rickshaws for the trip up to Sajjangarh Monsoon Palace as the road is steep and private cars/taxis have parking restrictions at the top.
* Wear comfortable slip-on footwear as you will need to remove shoes frequently at temples and historic palace sections.

