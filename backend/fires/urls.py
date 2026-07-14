# Заглушка urls для приложения fires
# Здесь регистрируются реальные вьюхи: FireViewSet, ImportViewSet,
# DangerBoardView, DashboardStatsView, SeasonComparisonView и т.д.

from django.urls import path
from django.http import JsonResponse

from . import views


def health(_request):
    return JsonResponse({'status': 'ok', 'app': 'fires'})


urlpatterns = [
    path('health/', health),
    path('districts/', views.DistrictsGeoJsonView.as_view()),
    path('fires/create/', views.FireCreateView.as_view()),
    path('fires/', views.FiresGeoJsonView.as_view()),
    path('danger-layer/', views.DangerLayerView.as_view()),
    # Заглушки для будущих эндпоинтов:
    # path('fires/import/forest/', ForestFireImportView.as_view()),
    # path('fires/import/techno/', TechnoFireImportView.as_view()),
    # path('imports/', ImportBatchViewSet.as_view({'get': 'list'})),
    # path('danger/board/', DangerBoardView.as_view()),
    # path('dashboard/stats/', DashboardStatsView.as_view()),
    # path('comparison/', SeasonComparisonView.as_view()),
]