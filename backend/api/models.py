from django.db import models


class Analysis(models.Model):
    question = models.TextField()
    answer = models.TextField()
    scores = models.JSONField(default=dict)
    lat = models.FloatField(null=True)
    lng = models.FloatField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
