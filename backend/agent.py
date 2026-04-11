import json
import anthropic
from dotenv import load_dotenv
from tools import get_population

load_dotenv()

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
    }
]

# This maps tool names to actual Python functions
TOOL_FUNCTIONS = {
    "get_population": get_population
}
