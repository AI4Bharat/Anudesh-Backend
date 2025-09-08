from django.urls import path, include
from rest_framework import routers
from loging.views import TransliterationSelectionViewSet, TranscriptionSelectionViewSet

router = routers.DefaultRouter()

urlpatterns = [
    path("", include(router.urls)),
    path(
        "transliteration_selection/",
        TransliterationSelectionViewSet.as_view(),
        name="transliteration_selection",
    ),
    path(
        "transcription_selection/",
        TranscriptionSelectionViewSet.as_view(),
        name="transcription_selection",
    ),
]
