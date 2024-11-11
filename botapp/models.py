from django.db import models

# Create your models here.

class User(models.Model):
    telegram_id = models.CharField(max_length=100, unique=True)
    wallet_address = models.CharField(max_length=42, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_task_timestamp = models.DateTimeField(null=True)

class Task(models.Model):
    TASK_TYPES = [
        ('AUDIO', 'Audio transcription'),
        ('IMAGE', 'Image submission'),
        ('TEXT', 'Text explanation')
    ]
    
    task_type = models.CharField(max_length=10, choices=TASK_TYPES)
    prompt = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
class Submission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    content = models.TextField()  # Store file path or text content
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_valid = models.BooleanField(default=False)
