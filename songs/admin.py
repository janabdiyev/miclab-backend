from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Model
from .models import Song, Category, Favorite, UserProfile
from django.core.files.base import ContentFile


class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


class SongAdmin(admin.ModelAdmin):
    list_display = ['title', 'artist', 'category',
                    'duration', 'created_at', 'file_status']
    list_filter = ['category', 'created_at', 'is_active']
    search_fields = ['title', 'artist']
    readonly_fields = ['created_at', 'updated_at', 'file_preview', 'duration']

    fieldsets = (
        ('Song Information', {
            'fields': ('title', 'artist', 'category', 'thumbnail')
        }),
        ('Audio & Lyrics Files', {
            'fields': ('audio_file', 'lyrics_file', 'file_preview'),
            'description': 'Upload both audio (.mp3, .wav, .flac) and lyrics (.vtt) files. Audio will be converted to M4A.'
        }),
        ('Duration (Auto-detected)', {
            'fields': ('duration',),
            'description': 'Duration is automatically detected from audio file'
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )

    def save_model(self, request, obj, form, change):
        """Custom save to handle audio conversion"""
        import os
        import subprocess
        from django.conf import settings
        import tempfile

        # Auto-detect duration if not set
        if obj.audio_file and (not obj.duration or obj.duration == 0):
            audio_file = obj.audio_file

            # Save to temp file to read duration
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.name)[1]) as tmp:
                for chunk in audio_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            try:
                cmd = [
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1:noprint_wrappers=1',
                    tmp_path
                ]
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=30)

                if result.returncode == 0 and result.stdout.strip():
                    obj.duration = int(float(result.stdout.strip()))
                else:
                    obj.duration = int(audio_file.size / 40000)
            except:
                obj.duration = 180
            finally:
                try:
                    os.remove(tmp_path)
                except:
                    pass

        # Generate filename from artist - title (normalize underscores)
        filename = f"{obj.artist} - {obj.title}"
        filename = filename.replace(
            '/', '_').replace('\\', '_').replace('"', '')
        filename_normalized = filename.replace(' ', '_')

        # Convert audio to M4A if needed
        if obj.audio_file:
            ext = os.path.splitext(obj.audio_file.name)[1].lower()

            # Save to temp file
            temp_audio_path = os.path.join(
                settings.MEDIA_ROOT, f'temp_audio{ext}')

            with open(temp_audio_path, 'wb') as f:
                for chunk in obj.audio_file.chunks():
                    f.write(chunk)

            # Convert to M4A if needed
            if ext in ['.mp3', '.wav', '.flac', '.ogg']:
                try:
                    output_path = os.path.join(
                        settings.MEDIA_ROOT, 'temp_audio.m4a')
                    cmd = [
                        'ffmpeg',
                        '-i', temp_audio_path,
                        '-c:a', 'aac',
                        '-b:a', '192k',
                        '-y',
                        output_path
                    ]
                    subprocess.run(cmd, capture_output=True, timeout=300)
                    if os.path.exists(temp_audio_path):
                        os.remove(temp_audio_path)
                    temp_audio_path = output_path
                except Exception as e:
                    print(f"Conversion error: {e}")

            # Read converted file and save via Django FileField
            with open(temp_audio_path, 'rb') as f:
                audio_content = f.read()

            # Use Django's ContentFile to properly store in upload_to location
            final_audio_filename = f"{filename_normalized}.m4a"
            obj.audio_file.save(final_audio_filename,
                                ContentFile(audio_content), save=False)

            # Clean up temp
            try:
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)
            except:
                pass

        # Rename VTT file if uploaded
        if obj.lyrics_file:
            ext = os.path.splitext(obj.lyrics_file.name)[1].lower()
            if ext == '.vtt':
                final_vtt_filename = f"{filename_normalized}.vtt"
                # Read the file content
                vtt_content = obj.lyrics_file.read()
                # Re-save with normalized name
                obj.lyrics_file.save(final_vtt_filename, ContentFile(vtt_content), save=False)

        super().save_model(request, obj, form, change)

    def file_status(self, obj):
        """Show if files exist"""
        audio = "✅" if obj.audio_file else "❌"
        lyrics = "✅" if obj.lyrics_file else "❌"
        return format_html(f"Audio: {audio} Lyrics: {lyrics}")
    file_status.short_description = "Files"

    def file_preview(self, obj):
        """Show file links"""
        if not obj.id:
            return "Save song first"

        html = "<strong>Current Files:</strong><br>"
        if obj.audio_file:
            html += f"🎵 <a href='{obj.audio_file.url}' target='_blank'>{obj.audio_file.name}</a><br>"
        else:
            html += "🎵 No audio file<br>"

        if obj.lyrics_file:
            html += f"🎤 <a href='{obj.lyrics_file.url}' target='_blank'>{obj.lyrics_file.name}</a><br>"
        else:
            html += "🎤 No lyrics file<br>"

        return format_html(html)
    file_preview.short_description = "File Preview"


class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'song', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__username', 'song__title']


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'subscription_type']
    list_filter = ['subscription_type']
    readonly_fields = ['created_at', 'updated_at']


admin.site.register(Song, SongAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Favorite, FavoriteAdmin)
admin.site.register(UserProfile, UserProfileAdmin)