from django.urls import path
from . import api_views

urlpatterns = [
    path('sources/', api_views.SourceListCreateAPIView.as_view(), name='api-source-list-create'),
    path('review-word/<int:pk>/', api_views.ReviewWordAPIView.as_view(), name='api-review-word'),
    path('mark-known/', api_views.MarkWordAsKnownAPIView.as_view(), name='api-mark-known'),
    path('next-word/', api_views.NextWordAPIView.as_view(), name='api-next-word'),
    path('chart-data/', api_views.ChartDataAPIView.as_view(), name='api-chart-data'),
    path('delete-source/<int:source_id>/', api_views.DeleteSourceAPIView.as_view(), name='api-delete-source'),
] 