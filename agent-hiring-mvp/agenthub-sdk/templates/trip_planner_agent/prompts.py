# Trip Planner Agent Prompts

trip_analysis_instructions = """
Analyze the following trip request and extract key information:

User Input: {user_input}

Today's date is {date}.

You are a travel planning expert. Your task is to extract specific trip details from the user's request.

CRITICAL: You MUST extract the exact destination mentioned in the user input. Do NOT make assumptions or change the destination.

Extract the following information:

1. destination: The specific city, country, or region they want to visit (REQUIRED - use exactly what the user specified)
2. month: Preferred month for the trip (optional - choose from: january, february, march, april, may, june, july, august, september, october, november, december)
3. travel_days: Number of travel days as an integer (optional - default to 7 if not specified)
4. budget_level: Choose from "budget", "moderate", or "luxury" (REQUIRED)
5. trip_type: Choose from "leisure", "business", "adventure", "cultural", "romantic", "family", "solo", or "group" (REQUIRED)
6. preferences: User interests and preferences like "art, food, nature, history" (REQUIRED)
7. group_size: Number of travelers as an integer (REQUIRED)

IMPORTANT RULES:
- Use the EXACT destination mentioned in the user input
- Do NOT change or substitute the destination
- If the user says "Vienna, Austria", use "Vienna, Austria" - NOT "Rome, Italy" or any other place
- If no month is specified or if month is "Not specified", set month to null (not "null" string)
- If no travel days are specified, use 7 as default
- If no budget is mentioned, assume "moderate"
- If no trip type is mentioned, assume "leisure"
- If no preferences are mentioned, assume "general travel"
- If no group size is mentioned, assume 2 travelers

CRITICAL: Ensure all fields have actual values, not empty strings. For month, use null (not "null" string) when no month is specified.
"""

destination_research_prompt = """
Research the destination: {destination}

Trip Type: {trip_type}
Budget Level: {budget_level}
User Preferences: {preferences}
Travel Days: {travel_days} days
Preferred Month: {month if month else "Not specified"}

Today's date is {date}.

Please provide comprehensive information about this destination including:

1. Description: Overview of the destination, its highlights, and what makes it special
2. Best Time to Visit: Optimal seasons and months for visiting
3. Weather Info: Typical weather conditions, climate, and what to expect
4. Local Customs: Important cultural information, etiquette, and local customs
5. Safety Tips: Safety considerations and important information for travelers

Focus on information that would be relevant for a {trip_type} trip with {budget_level} budget level.

CRITICAL: Ensure all fields have actual values, not empty strings.
"""

accommodation_research_prompt = """
Research accommodation options for: {destination}

Budget Level: {budget_level}
Trip Duration: {trip_duration} days
User Preferences: {preferences}

Today's date is {date}.

You are a travel accommodation expert. Provide detailed accommodation recommendations for {destination}.

IMPORTANT: You must provide 3-5 accommodation recommendations with ALL required fields filled.

For each accommodation, provide:
- name: Full name of the accommodation (REQUIRED)
- type: Type of accommodation (hotel, hostel, apartment, resort, etc.) (REQUIRED)
- price_range: Price range per night (e.g., "$100-200/night") (REQUIRED)
- location: Specific location and neighborhood (REQUIRED)
- amenities: Key amenities and features (REQUIRED)
- pros: Positive aspects of this accommodation (REQUIRED)
- cons: Negative aspects or limitations (REQUIRED)
- booking_tips: Tips for booking this accommodation (REQUIRED)

Also provide general tips for booking accommodations in this destination.

Focus on options suitable for {budget_level} budget level and {trip_duration} day stay.

CRITICAL: Ensure all fields have actual values, not empty strings.
"""

activity_research_prompt = """
Research activities and attractions for: {destination}

Trip Type: {trip_type}
Budget Level: {budget_level}
Trip Duration: {trip_duration} days
User Preferences: {preferences}

Today's date is {date}.

You are a travel activities expert. Provide detailed activity and attraction recommendations for {destination}.

IMPORTANT: You must provide 5-8 activity recommendations with ALL required fields filled.

For each activity, provide:
- name: Full name of the activity or attraction (REQUIRED)
- type: Type of activity (museum, park, tour, experience, etc.) (REQUIRED)
- description: Detailed description and highlights (REQUIRED)
- cost: Cost and budget category (e.g., "$20-50") (REQUIRED)
- duration: Duration and time required (e.g., "2-3 hours") (REQUIRED)
- location: Specific location and accessibility (REQUIRED)
- best_time: Best time to visit (e.g., "Morning or late afternoon") (REQUIRED)
- booking_tips: Booking requirements and tips (REQUIRED)

Also provide general tips for activities and attractions in this destination.

Focus on activities suitable for {trip_type} trip with {budget_level} budget level.

CRITICAL: Ensure all fields have actual values, not empty strings.
"""

restaurant_research_prompt = """
Research dining options for: {destination}

Budget Level: {budget_level}
User Preferences: {preferences}

Today's date is {date}.

You are a dining expert. Provide detailed restaurant recommendations for {destination}.

IMPORTANT: You must provide 4-6 restaurant recommendations with ALL required fields filled.

For each restaurant, provide:
- name: Full name of the restaurant (REQUIRED)
- cuisine: Type of cuisine served (REQUIRED)
- price_range: Price range (e.g., "$", "$$", "$$$") (REQUIRED)
- location: Specific location and neighborhood (REQUIRED)
- specialties: Specialties and must-try dishes (REQUIRED)
- atmosphere: Atmosphere and dining experience (REQUIRED)
- reservation_tips: Reservation requirements and tips (REQUIRED)

Also provide general tips for dining in this destination.

Focus on restaurants suitable for {budget_level} budget level and consider local cuisine and specialties.

CRITICAL: Ensure all fields have actual values, not empty strings.
"""

day_planning_prompt = """
Create a detailed day-by-day itinerary for: {destination}

Trip Duration: {trip_duration} days
Preferred Month: {month}
Travel Days: {travel_days} days
Activities: {activities}
Restaurants: {restaurants}

Today's date is {date}.

You are a travel itinerary expert. Create detailed day-by-day plans for {destination}.

IMPORTANT: You must provide a plan for each day with ALL required fields filled.

For each day, provide:
- day: Day number (1, 2, 3, etc.) (REQUIRED)
- date: Day label (e.g., "Day 1", "Day 2") (REQUIRED)
- morning: Morning activities and timing (REQUIRED)
- lunch: Lunch recommendations (REQUIRED)
- afternoon: Afternoon activities and timing (REQUIRED)
- dinner: Dinner recommendations (REQUIRED)
- evening: Evening activities (if any) (REQUIRED)
- transportation: Transportation between activities (REQUIRED)
- estimated_cost: Estimated costs for the day (REQUIRED)
- tips: Tips and notes for the day (REQUIRED)

Make sure to:
- Balance activities and rest time
- Include meals at appropriate times
- Consider opening hours and best times to visit attractions
- Provide realistic timing estimates
- Include transportation logistics
- Vary the pace and intensity of activities

CRITICAL: Ensure all fields have actual values, not empty strings.
"""

final_itinerary_prompt = """
Create a comprehensive trip itinerary for: {destination}

Trip Details:
- Destination: {destination}
- Travel Period: {month} ({travel_days} days)
- Duration: {trip_duration} days
- Budget Level: {budget_level}
- Trip Type: {trip_type}
- Preferences: {preferences}

Please create a comprehensive trip itinerary that includes:

1. **Trip Summary and Understanding** - Start with a brief summary showing you understand the trip requirements:
   - Confirm the destination and travel period (e.g., "I understand you want to visit {destination} for {travel_days} days{(' in ' + month) if month != 'Not specified' else ''}")
   - Acknowledge the budget level and trip type (e.g., "This will be a {trip_type} trip with a {budget_level} budget")
   - Show understanding of the user's preferences (e.g., "I've focused on {preferences} based on your interests")
   - Mention any special requirements or constraints
   - Provide a brief overview of what makes this destination special for this type of trip

2. Trip Overview and Summary
3. Destination Information and Tips
4. Accommodation Recommendations
5. Activity and Attraction Guide
6. Dining Recommendations
7. Detailed Day-by-Day Itinerary
8. Budget Breakdown and Cost Estimates
9. Transportation Information
10. Packing List and Travel Tips
11. Emergency Information and Contacts

Format the itinerary in a clear, organized manner with sections, bullet points, and helpful formatting. Make it easy to read and follow.

Focus on creating a practical, enjoyable trip that matches the {budget_level} budget level and {trip_type} trip style.

Provide a comprehensive, detailed itinerary that the traveler can use as their complete trip guide.
"""

Research Information:
- Destination Info: {destination_info}
- Accommodations: {accommodations}
- Activities: {activities}
- Restaurants: {restaurants}
- Day Plans: {day_plans}

Today's date is {date}.

Please create a comprehensive trip itinerary that includes:

1. Trip Overview and Summary
2. Destination Information and Tips
3. Accommodation Recommendations
4. Activity and Attraction Guide
5. Dining Recommendations
6. Detailed Day-by-Day Itinerary
7. Budget Breakdown and Cost Estimates
8. Transportation Information
9. Packing List and Travel Tips
10. Emergency Information and Contacts

Format the itinerary in a clear, organized manner with sections, bullet points, and helpful formatting. Make it easy to read and follow.

Focus on creating a practical, enjoyable trip that matches the {budget_level} budget level and {trip_type} trip style.

Provide a comprehensive, detailed itinerary that the traveler can use as their complete trip guide.
""" 