from rest_framework import serializers
from .models import Song, Category, Favorite, UserProfile
from django.contrib.auth.models import User
from .models import Recording


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class RecordingSerializer(serializers.ModelSerializer):
    song_title = serializers.CharField(source='song.title', read_only=True)
    user_username = serializers.CharField(
        source='user.username', read_only=True)

    class Meta:
        model = Recording
        fields = ['id', 'user', 'user_username', 'song', 'song_title', 'audio_file',
                  'recording_id', 'duration', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class SongListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    lyrics = serializers.SerializerMethodField()
    audio_url = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Song
        fields = ['id', 'title', 'artist', 'category', 'thumbnail',
                  'duration', 'audio_url', 'lyrics', 'is_favorite']

    def get_lyrics(self, obj):
        if obj.lyrics_file:
            try:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.lyrics_file.url)
                return obj.lyrics_file.url
            except:
                return None
        return None

    def get_audio_url(self, obj):
        request = self.context.get('request')
        if obj.audio_file:
            url = request.build_absolute_uri(
                obj.audio_file.url) if request else obj.audio_file.url
            url = url.replace('.mp3', '.m4a')
            return url
        return None

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(user=request.user, song=obj).exists()
        return False


class SongDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    lyrics = serializers.SerializerMethodField()
    audio_url = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Song
        fields = ['id', 'title', 'artist', 'category', 'thumbnail',
                  'duration', 'audio_url', 'lyrics', 'is_favorite', 'created_at']

    def get_lyrics(self, obj):
        if obj.lyrics_file:
            try:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.lyrics_file.url)
                return obj.lyrics_file.url
            except:
                return None
        return None

    def get_audio_url(self, obj):
        request = self.context.get('request')
        if obj.audio_file:
            url = request.build_absolute_uri(
                obj.audio_file.url) if request else obj.audio_file.url
            url = url.replace('.mp3', '.m4a')
            return url
        return None

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(user=request.user, song=obj).exists()
        return False


class FavoriteSerializer(serializers.ModelSerializer):
    song = SongListSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ['id', 'song', 'added_at']


class UserProfileSerializer(serializers.ModelSerializer):
    subscription_status = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ['subscription_type', 'trial_start_date', 'trial_end_date',
                  'subscription_start_date', 'subscription_end_date', 'subscription_status']

    def get_subscription_status(self, obj):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        if obj.subscription_type == 'free':
            if obj.trial_end_date and obj.trial_end_date > now:
                days_left = (obj.trial_end_date - now).days
                return f"Free trial - {days_left} days left"
            else:
                return "Trial expired"
        else:
            if obj.subscription_end_date and obj.subscription_end_date > now:
                days_left = (obj.subscription_end_date - now).days
                return f"Premium - {days_left} days left"
            else:
                return "Subscription expired"
