from django.db import models
from pgvector.django import VectorField

class Document(models.Model):
    content = models.TextField()
    embedding = VectorField(dimensions=1536)  # OpenAI ada-002 embedding dimension
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['embedding']),
        ] 