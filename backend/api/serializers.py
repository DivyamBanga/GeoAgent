from rest_framework import serializers
from .models import Analysis


class AnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Analysis
        fields = ["id", "question", "answer", "scores", "lat", "lng", "created_at"]
