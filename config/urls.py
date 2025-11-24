from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from songs.views import SongViewSet, CategoryViewSet, FavoriteViewSet, UserProfileViewSet, RecordingViewSet, upload_song_page
from auth_app.views import AuthViewSet
import os

# Create router and register viewsets
router = DefaultRouter()
router.register(r'songs', SongViewSet, basename='song')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'favorites', FavoriteViewSet, basename='favorite')
router.register(r'profile', UserProfileViewSet, basename='profile')
router.register(r'recordings', RecordingViewSet, basename='recording')
router.register(r'auth', AuthViewSet, basename='auth')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('upload/', upload_song_page, name='upload_song'),
    path('api/', include(router.urls)),
]

# Serve media files in development and production (Render)
if settings.DEBUG or os.getenv('RENDER'):
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
