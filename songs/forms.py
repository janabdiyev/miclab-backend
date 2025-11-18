from django import forms
from .models import Song, Category
import subprocess
import os


class SongUploadForm(forms.ModelForm):
    lyrics_text = forms.CharField(
        label="Lyrics with Timings (LRC Format)",
        widget=forms.Textarea(attrs={
            'rows': 10,
            'placeholder': '[00:15.30] First line\n[00:20.50] Second line\n...',
            'style': 'font-family: monospace; font-size: 12px;'
        }),
        required=True,
        help_text="Paste lyrics in LRC format or plain text"
    )

    class Meta:
        model = Song
        fields = ['title', 'artist', 'category', 'audio_file', 'thumbnail']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Song Title'
            }),
            'artist': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Artist Name'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'audio_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.mp3,.m4a,.wav,.flac,.ogg'
            }),
            'thumbnail': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }

    def clean_audio_file(self):
        """Get duration from audio file"""
        audio_file = self.cleaned_data.get('audio_file')

        if audio_file:
            # Save to temp file to read duration
            import tempfile
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
                    duration_seconds = int(float(result.stdout.strip()))
                    self.duration = duration_seconds
                    print(
                        f"✅ Detected duration: {duration_seconds} seconds ({duration_seconds//60}:{duration_seconds % 60:02d})")
                else:
                    file_size = audio_file.size
                    self.duration = max(int(file_size / 40000), 60)
                    print(f"⚠️ Estimated duration: {self.duration} seconds")

            except Exception as e:
                print(f"❌ Error reading duration: {e}")
                self.duration = 180
            finally:
                try:
                    os.remove(tmp_path)
                except:
                    pass

        return audio_file
