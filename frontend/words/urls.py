from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WordViewSet, ReviewLogViewSet, UserProfileViewSet, TextCategoryViewSet, DictionaryWordViewSet, register

router = DefaultRouter()
router.register(r'words', WordViewSet, basename='word')
router.register(r'reviews', ReviewLogViewSet, basename='review')
router.register(r'profile', UserProfileViewSet, basename='profile')
router.register(r'categories', TextCategoryViewSet, basename='category')
router.register(r'dictionary', DictionaryWordViewSet, basename='dictionary')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', register, name='register'),
] 