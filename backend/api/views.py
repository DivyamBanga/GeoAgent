import json
import sys
import os

# Add the backend directory to sys.path so we can import agent.py and tools.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from agent import run_agent, run_agent_streaming
from .models import Analysis
from .serializers import AnalysisSerializer


@api_view(["POST"])
def analyze(request):
    """Main endpoint: send a question, get an analysis back."""
    question = request.data.get("question", "")
    if not question:
        return Response({"error": "No question provided"}, status=400)

    result = run_agent(question)

    # Save the analysis to the database
    analysis = Analysis.objects.create(
        question=question,
        answer=result,
        scores=request.data.get("scores", {}),
        lat=request.data.get("lat"),
        lng=request.data.get("lng"),
    )

    return Response({
        "id": analysis.id,
        "question": question,
        "answer": result,
        "created_at": analysis.created_at.isoformat(),
    })


@api_view(["POST"])
def analyze_stream(request):
    """Streaming endpoint: sends agent events as they happen via SSE."""
    question = request.data.get("question", "")
    if not question:
        return Response({"error": "No question provided"}, status=400)

    def event_stream():
        collected_scores = {}
        final_answer = ""

        for event in run_agent_streaming(question):
            # Collect scores from tool results as they come in
            if event["type"] == "tool_result":
                result = event.get("result", {})
                if "score" in result:
                    collected_scores[event["tool"]] = result["score"]

            if event["type"] == "answer":
                final_answer = event["content"]

            yield f"data: {json.dumps(event)}\n\n"

        # Save analysis after streaming completes
        analysis = Analysis.objects.create(
            question=question,
            answer=final_answer,
            scores=collected_scores,
            lat=request.data.get("lat"),
            lng=request.data.get("lng"),
        )

        yield f"data: {json.dumps({'type': 'saved', 'id': analysis.id})}\n\n"
        yield "data: {\"type\": \"done\"}\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream"
    )
    response["Cache-Control"] = "no-cache"
    return response


@api_view(["GET"])
def analyses_list(request):
    """List all past analyses, most recent first."""
    analyses = Analysis.objects.all()
    serializer = AnalysisSerializer(analyses, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def health(request):
    """Health check endpoint."""
    return Response({"status": "ok"})
