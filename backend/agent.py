import json
import os
import anthropic
from dotenv import load_dotenv
from tools import get_population, find_competitors, get_median_income

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

client = anthropic.Anthropic()

# This is the tool DEFINITION — tells Claude what the function does
tools = [
    {
        "name": "get_population",
        "description": "Get the population count within a radius of a geographic point. Use this when the user asks about population, demographics, or how many people live near a location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {
                    "type": "number",
                    "description": "Latitude of the center point"
                },
                "lng": {
                    "type": "number",
                    "description": "Longitude of the center point"
                },
                "radius_km": {
                    "type": "number",
                    "description": "Radius in kilometers to search within"
                }
            },
            "required": ["lat", "lng", "radius_km"]
        }
    },
    {
        "name": "find_competitors",
        "description": "Find competing businesses near a geographic point. Use this when the user asks about competition, nearby businesses, or market saturation in an area.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {
                    "type": "number",
                    "description": "Latitude of the center point"
                },
                "lng": {
                    "type": "number",
                    "description": "Longitude of the center point"
                },
                "business_type": {
                    "type": "string",
                    "description": "Type of business to search for (e.g. 'coffee_shop', 'restaurant')"
                },
                "radius_km": {
                    "type": "number",
                    "description": "Radius in kilometers to search within"
                }
            },
            "required": ["lat", "lng", "business_type", "radius_km"]
        }
    },
    {
        "name": "get_median_income",
        "description": "Get the median household income and average household spend near a location. Use this when the user asks about income, spending power, or economic demographics of an area.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {
                    "type": "number",
                    "description": "Latitude of the location"
                },
                "lng": {
                    "type": "number",
                    "description": "Longitude of the location"
                }
            },
            "required": ["lat", "lng"]
        }
    }
]

# This maps tool names to actual Python functions
TOOL_FUNCTIONS = {
    "get_population": get_population,
    "find_competitors": find_competitors,
    "get_median_income": get_median_income
}


def run_agent(user_message: str) -> str:
    """Run one turn of the agent loop."""
    messages = [{"role": "user", "content": user_message}]

    system = """You are GeoAgent, a location intelligence analyst.
    When analyzing a location, use ALL relevant tools to gather data.
    Always provide specific numbers from the tools, not guesses.
    If the user mentions Kitchener downtown, use lat=43.45, lng=-80.49.
    If they mention Waterloo uptown, use lat=43.47, lng=-80.52.

    After gathering data, provide:
    1. An overall score (0-100) for the location based on the tool scores
    2. The top 3 positive factors
    3. The top 3 risks
    4. A clear recommendation (Go / Caution / Avoid)
    Format your response clearly with headers."""

    # Step 1: Send message to Claude with tool definitions
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system,
        tools=tools,
        messages=messages
    )

    # Step 2: Check if Claude wants to use a tool
    while response.stop_reason == "tool_use":
        # Find the tool use block in the response
        tool_use_block = next(
            block for block in response.content if block.type == "tool_use"
        )
        tool_name = tool_use_block.name
        tool_input = tool_use_block.input

        print(f"  [Agent is calling: {tool_name}({tool_input})]")

        # Step 3: Execute the actual Python function
        result = TOOL_FUNCTIONS[tool_name](**tool_input)

        # Step 4: Send the result back to Claude
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_block.id,
                    "content": json.dumps(result)
                }
            ]
        })

        # Step 5: Claude generates final answer using the tool result
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
            tools=tools,
            messages=messages
        )

    # Extract text response
    text_blocks = [b.text for b in response.content if hasattr(b, "text")]
    return "\n".join(text_blocks)


if __name__ == "__main__":
    while True:
        q = input("\nYou: ")
        if q.lower() in ("quit", "exit"):
            break
        answer = run_agent(q)
        print(f"\nGeoAgent: {answer}")
