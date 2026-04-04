import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()
conversation = []

system_prompt = """You are GeoAgent, a location intelligence analyst.
You help people find the best locations for their businesses.
You think about demographics, competition, foot traffic, and zoning."""

while True:
    user_input = input("\nYou: ")
    if user_input.lower() in ("quit", "exit"):
        break

    conversation.append({"role": "user", "content": user_input})

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=conversation
    )

    assistant_message = response.content[0].text
    conversation.append({"role": "assistant", "content": assistant_message})
    print(f"\nGeoAgent: {assistant_message}")
