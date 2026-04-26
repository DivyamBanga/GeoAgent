import json
import sys
import os

# Add the backend directory to sys.path so we can import agent.py and tools.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from agent import run_agent, run_agent_streaming


@api_view(["POST"])
def analyze(request):
    """Main endpoint: send a question, get an analysis back."""
    question = request.data.get("question", "")
    if not question:
        return Response({"error": "No question provided"}, status=400)

    result = run_agent(question)
    return Response({
        "question": question,
        "answer": result
    })


@api_view(["POST"])
def analyze_stream(request):
    """Streaming endpoint: sends agent events as they happen via SSE."""
    question = request.data.get("question", "")
    if not question:
        return Response({"error": "No question provided"}, status=400)

    def event_stream():
        for event in run_agent_streaming(question):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: {\"type\": \"done\"}\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream"
    )
    response["Cache-Control"] = "no-cache"
    return response


@api_view(["GET"])
def health(request):
    """Health check endpoint."""
    return Response({"status": "ok"})
