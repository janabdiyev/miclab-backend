from rest_framework import viewsets, status, permissions
from datetime import datetime, timezone, timedelta
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.files.base import ContentFile
from django.http import FileResponse
from .models import Song, Category, Favorite, UserProfile, Recording
from .serializers import SongDetailSerializer, SongListSerializer, CategorySerializer, FavoriteSerializer, UserProfileSerializer, RecordingSerializer
from .forms import SongUploadForm
import os
import subprocess
import tempfile
import time
import uuid


class AllowAnonReadOnly(permissions.BasePermission):
    """Allow anonymous users to read songs (trial access)"""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:  # GET requests
            return True
        return request.user and request.user.is_authenticated


class SongViewSet(viewsets.ModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongDetailSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_serializer_class(self):
        if self.action == 'list':
            return SongListSerializer
        return SongDetailSerializer

    @action(detail=False, methods=['post'])
    def upload_song(self, request):
        """
        Upload a new song with audio and lyrics files

        Usage:
        curl -X POST http://192.168.1.40:8000/api/songs/upload_song/ \
          -H "Authorization: Token YOUR_TOKEN" \
          -F "title=Song Name" \
          -F "artist=Artist Name" \
          -F "category=1" \
          -F "duration=180" \
          -F "audio_file=@/path/to/song.mp3" \
          -F "lyrics_file=@/path/to/song.lrc"
        """
        try:
            title = request.data.get('title')
            artist = request.data.get('artist')
            category_id = request.data.get('category')
            duration = request.data.get('duration')
            audio_file = request.FILES.get('audio_file')
            lyrics_file = request.FILES.get('lyrics_file')

            if not all([title, artist, category_id, duration, audio_file, lyrics_file]):
                return Response(
                    {'error': 'Missing required fields: title, artist, category, duration, audio_file, lyrics_file'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            category = Category.objects.get(id=category_id)

            song = Song.objects.create(
                title=title,
                artist=artist,
                category=category,
                duration=int(duration),
                audio_file=audio_file,
                lyrics_file=lyrics_file
            )

            serializer = SongDetailSerializer(
                song, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Category.DoesNotExist:
            return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def update_audio(self, request, pk=None):
        """
        Update only the audio file for a song

        Usage:
        curl -X POST http://192.168.1.40:8000/api/songs/1/update_audio/ \
          -H "Authorization: Token YOUR_TOKEN" \
          -F "audio_file=@/path/to/new_song.mp3"
        """
        try:
            song = self.get_object()
            audio_file = request.FILES.get('audio_file')

            if not audio_file:
                return Response({'error': 'audio_file is required'}, status=status.HTTP_400_BAD_REQUEST)

            song.audio_file = audio_file
            song.save()

            serializer = SongDetailSerializer(
                song, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def update_lyrics(self, request, pk=None):

        try:
            song = self.get_object()
            lyrics_file = request.FILES.get('lyrics_file')

            if not lyrics_file:
                return Response({'error': 'lyrics_file is required'}, status=status.HTTP_400_BAD_REQUEST)

            song.lyrics_file = lyrics_file
            song.save()

            serializer = SongDetailSerializer(
                song, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class FavoriteViewSet(viewsets.ModelViewSet):
    queryset = Favorite.objects.all()
    serializer_class = FavoriteSerializer


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer


class RecordingViewSet(viewsets.ModelViewSet):
    queryset = Recording.objects.all()
    serializer_class = RecordingSerializer
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        try:
            song_id = request.data.get('song')
            duration = request.data.get('duration')
            audio_file = request.FILES.get('audio_file')

            if not all([song_id, audio_file]):
                return Response({'error': 'Missing song or audio_file'}, status=400)

            song = Song.objects.get(id=song_id)
            recording_id = f"{request.user.id}_{song_id}_{int(time.time())}"

            recording = Recording.objects.create(
                user=request.user,
                song=song,
                audio_file=audio_file,
                recording_id=recording_id,
                duration=int(duration) if duration else 0
            )

            return Response(RecordingSerializer(recording).data, status=201)

        except Song.DoesNotExist:
            return Response({'error': 'Song not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=400)


def convert_to_m4a(input_file_path):
    """Convert audio file to M4A format using ffmpeg"""
    try:
        output_file_path = input_file_path.replace(
            os.path.splitext(input_file_path)[1], '.m4a')

        # Run ffmpeg conversion
        cmd = [
            'ffmpeg',
            '-i', input_file_path,
            '-c:a', 'aac',
            '-b:a', '192k',
            '-y',  # Overwrite output file
            output_file_path
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            # Delete original file
            os.remove(input_file_path)
            print(f"✅ Converted to M4A: {output_file_path}")
            return output_file_path
        else:
            print(f"❌ FFmpeg error: {result.stderr}")
            return input_file_path
    except Exception as e:
        print(f"❌ Conversion error: {e}")
        return input_file_path


# Web form view for admin dashboard
@login_required
def upload_song_page(request):
    """Simple form to upload song with lyrics"""

    if request.method == 'POST':
        form = SongUploadForm(request.POST, request.FILES)
        if form.is_valid():
            song = form.save(commit=False)

            # Set duration from audio file analysis
            if hasattr(form, 'duration'):
                song.duration = form.duration
            else:
                song.duration = 180  # Default fallback

            # Generate filename from artist - title
            filename = f"{song.artist} - {song.title}"
            filename = filename.replace(
                '/', '_').replace('\\', '_').replace('"', '')

            # Save audio file with custom name and convert to M4A
            if song.audio_file:
                ext = os.path.splitext(song.audio_file.name)[1].lower()

                # Save original file temporarily
                temp_audio_path = os.path.join(
                    settings.MEDIA_ROOT, 'songs', 'audio', f"temp_{song.audio_file.name}")
                os.makedirs(os.path.dirname(temp_audio_path), exist_ok=True)

                with open(temp_audio_path, 'wb') as f:
                    for chunk in song.audio_file.chunks():
                        f.write(chunk)

                # Convert to M4A if not already
                if ext in ['.mp3', '.wav', '.flac', '.ogg']:
                    print(f"🎵 Converting {ext} to M4A...")
                    converted_path = convert_to_m4a(temp_audio_path)
                    m4a_filename = f"songs/audio/{filename}.m4a"
                else:
                    # Already M4A or AAC
                    converted_path = temp_audio_path
                    m4a_filename = f"songs/audio/{filename}.m4a"

                # Read converted file and save to media
                with open(converted_path, 'rb') as f:
                    song.audio_file = ContentFile(f.read(), name=m4a_filename)

            # Save lyrics from textarea
            lyrics_text = form.cleaned_data.get('lyrics_text', '')
            if lyrics_text:
                lyrics_filename = f"songs/audio/{filename}.lrc"
                lyrics_path = os.path.join(
                    settings.MEDIA_ROOT, lyrics_filename)

                # Create directory if needed
                os.makedirs(os.path.dirname(lyrics_path), exist_ok=True)

                # Save lyrics to file
                with open(lyrics_path, 'w', encoding='utf-8') as f:
                    f.write(lyrics_text)

                song.lyrics_file.name = lyrics_filename

            song.save()

            return redirect('admin:songs_song_change', song.id)
    else:
        form = SongUploadForm()

    return render(request, 'admin/song_upload.html', {'form': form})


# VOCAL SEPARATION ENDPOINT
@api_view(['POST'])
# Allow without auth for now - change to IsAuthenticated after testing
@permission_classes([AllowAny])
def separate_vocals(request):
    """
    Separate vocals from mixed audio (voice + music bleed + backing track)
    Returns isolated vocals only using Demucs
    """
    try:
        # IMPORT INSIDE FUNCTION - Don't crash app if not installed
        try:
            import torch
            import torchaudio
            from demucs.pretrained import get_model
            from demucs.apply import apply_model
        except ImportError as e:
            print(f"❌ Demucs not installed: {e}")
            return Response({'error': 'Vocal separation not available - dependencies not installed'}, status=503)

        audio_file = request.FILES.get('audio')
        if not audio_file:
            return Response({'error': 'audio file required'}, status=400)

        print("🎵 Starting vocal separation...")

        # Save uploaded file temporarily
        temp_input = os.path.join(
            tempfile.gettempdir(), f"mixed_{uuid.uuid4()}.m4a")
        with open(temp_input, 'wb') as f:
            for chunk in audio_file.chunks():
                f.write(chunk)

        print(f"📥 Saved input: {temp_input}")

        # Convert to WAV for Demucs
        temp_wav = temp_input.replace('.m4a', '.wav')
        result = subprocess.run([
            'ffmpeg', '-i', temp_input, '-ar', '44100', '-ac', '2', '-y', temp_wav
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ FFmpeg error: {result.stderr}")
            return Response({'error': 'Audio conversion failed'}, status=500)

        print(f"✅ Converted to WAV: {temp_wav}")

        print("📦 Loading Demucs model...")
        model = get_model('htdemucs')
        model.eval()

        # Load audio
        print("🎧 Loading audio...")
        wav, sr = torchaudio.load(temp_wav)

        # Ensure stereo
        if wav.shape[0] == 1:
            wav = wav.repeat(2, 1)

        print(f"🎼 Audio shape: {wav.shape}, Sample rate: {sr}")

        # Separate (htdemucs returns: drums, bass, other, vocals)
        print("🔬 Separating vocals (this takes 10-30 seconds)...")
        with torch.no_grad():
            sources = apply_model(model, wav[None], device='cpu')

        # Extract vocals (index 3)
        vocals = sources[0, 3]  # [channels, samples]

        print(f"🎤 Vocals extracted: {vocals.shape}")

        # Save isolated vocals
        output_wav = os.path.join(
            tempfile.gettempdir(), f"vocals_{uuid.uuid4()}.wav")
        torchaudio.save(output_wav, vocals, sr)

        print(f"💾 Saved vocals WAV: {output_wav}")

        # Convert to M4A
        output_m4a = output_wav.replace('.wav', '.m4a')
        result = subprocess.run([
            'ffmpeg', '-i', output_wav, '-c:a', 'aac', '-b:a', '192k', '-y', output_m4a
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ FFmpeg M4A conversion error: {result.stderr}")
            return Response({'error': 'Audio conversion failed'}, status=500)

        print(f"✅ Converted to M4A: {output_m4a}")

        # Cleanup
        try:
            os.remove(temp_input)
            os.remove(temp_wav)
            os.remove(output_wav)
            print("🗑️ Cleaned up temp files")
        except:
            pass

        # Return vocals file
        print("✅ Sending vocals back to client")
        return FileResponse(open(output_m4a, 'rb'), content_type='audio/m4a')

    except Exception as e:
        print(f"❌ Vocal separation error: {e}")
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=500)
