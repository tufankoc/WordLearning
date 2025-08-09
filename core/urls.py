from django.urls import path
from .views import (
    landing_page,
    dashboard,
    source_detail,
    settings_page,
    statistics_page,
    help_page,
    review_page,
    upgrade_page,
    register_view,
    profile_view,
    admin_dashboard,
    enhanced_api_demo,
)
from .api_views import (
    SourceListCreateAPIView,
    EnhancedSourceCreateAPIView,
    ReviewWordAPIView,
    MarkWordAsKnownAPIView,
    NextWordAPIView,
    DeleteSourceAPIView,
    DebugSourceTestAPIView,
    UserProfileAPIView
)

urlpatterns = [
    path('', landing_page, name='landing_page'),
    path('dashboard/', dashboard, name='dashboard'),
    path('source/<int:source_id>/words/', source_detail, name='source_detail'),
    path('review/', review_page, name='review_page'),
    path('settings/', settings_page, name='settings_page'),
    path('statistics/', statistics_page, name='statistics_page'),
    path('help/', help_page, name='help_page'),
    path('upgrade/', upgrade_page, name='upgrade_page'),
    path('profile/', profile_view, name='profile_page'),
    path('register/', register_view, name='register'),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('api-demo/', enhanced_api_demo, name='api_demo'),

    # API - Enhanced endpoints
    path('sources/enhanced/', EnhancedSourceCreateAPIView.as_view(), name='enhanced-source-create'),
    path('api/sources/enhanced/', EnhancedSourceCreateAPIView.as_view(), name='api-enhanced-source-create'),
    
    # API - Legacy endpoints
    path('api/sources/', SourceListCreateAPIView.as_view(), name='source-list-create'),
    path('api/review-word/<int:pk>/', ReviewWordAPIView.as_view(), name='review-word'),
    path('api/mark-known/', MarkWordAsKnownAPIView.as_view(), name='mark-word-known'),
    path('api/next-word/', NextWordAPIView.as_view(), name='next-word'),
    path('api/delete-source/<int:source_id>/', DeleteSourceAPIView.as_view(), name='delete-source'),
    path('api/profile/', UserProfileAPIView.as_view(), name='user-profile'),

    # Debug endpoint for testing
    path('debug/test/', DebugSourceTestAPIView.as_view(), name='debug-test'),
] 