from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Song(models.Model):
    title = models.CharField(max_length=200)
    artist = models.CharField(max_length=200)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True)
    audio_file = models.FileField(upload_to='songs/audio/')
    lyrics_file = models.FileField(upload_to='songs/audio/')
    thumbnail = models.ImageField(
        upload_to='songs/thumbnails/', null=True, blank=True)
    duration = models.IntegerField(help_text="Duration in seconds")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.artist} - {self.title}"


class Favorite(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='favorites')
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'song')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} - {self.song.title}"


class UserProfile(models.Model):
    SUBSCRIPTION_CHOICES = [
        ('free', 'Free Trial'),
        ('premium_monthly', 'Premium Monthly'),
        ('premium_yearly', 'Premium Yearly'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile')
    subscription_type = models.CharField(
        max_length=20, choices=SUBSCRIPTION_CHOICES, default='free')
    trial_start_date = models.DateTimeField(null=True, blank=True)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    subscription_start_date = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    stripe_customer_id = models.CharField(
        max_length=255, null=True, blank=True)
    stripe_subscription_id = models.CharField(
        max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.subscription_type}"


class Recording(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='recordings')
    song = models.ForeignKey(
        # <- ADD null=True, blank=True
        Song, on_delete=models.CASCADE, related_name='recordings', null=True, blank=True)
    audio_file = models.FileField(upload_to='myrecordings/')
    recording_id = models.CharField(max_length=100, unique=True)
    duration = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.recording_id}"


class TrialSession(models.Model):
    """Track anonymous trial users - 7 days access to song list"""
    device_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    trial_end_date = models.DateTimeField()

    def __str__(self):
        return f"Trial - {self.device_id}"

    def is_trial_active(self):
        from django.utils import timezone
        return timezone.now() < self.trial_end_date
