"""
Начальный набор API-эндпоинтов для MapView.
Расширяется реальными вьюхами (импорт, дашборд и т.д.) отдельно.
"""
import json
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.gis.db.models.functions import AsGeoJSON
from django.contrib.gis.geos import Point
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import District, Fire, FireDangerForecast


class DistrictsGeoJsonView(APIView):
    """GeoJSON границ районов для отображения на карте."""
    permission_classes = [AllowAny]

    def get(self, request):
        features = []
        for d in District.objects.annotate(geo=AsGeoJSON('geometry')):
            features.append({
                'type': 'Feature',
                'properties': {'id': d.id, 'name': d.name},
                'geometry': json.loads(d.geo),
            })
        return Response({'type': 'FeatureCollection', 'features': features})


class FiresGeoJsonView(APIView):
    """
    GeoJSON пожаров с фильтрами:
      ?date_from=YYYY-MM-DD
      ?date_to=YYYY-MM-DD
      ?category=forest|techno
      ?bbox=minLon,minLat,maxLon,maxLat
    """
    permission_classes = [AllowAny]

    def get(self, request):
        qs = Fire.objects.select_related('cause').annotate(geo=AsGeoJSON('location'))

        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        category = request.query_params.get('category')
        bbox = request.query_params.get('bbox')

        if date_from:
            qs = qs.filter(occurred_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(occurred_at__date__lte=date_to)
        if category:
            qs = qs.filter(category=category)
        if bbox:
            try:
                min_lon, min_lat, max_lon, max_lat = map(float, bbox.split(','))
                from django.contrib.gis.geos import Polygon
                bbox_poly = Polygon.from_bbox((min_lon, min_lat, max_lon, max_lat))
                bbox_poly.srid = 4326
                qs = qs.filter(location__within=bbox_poly)
            except (ValueError, TypeError):
                pass

        features = []
        for f in qs:
            features.append({
                'type': 'Feature',
                'properties': {
                    'id': f.id,
                    'category': f.category,
                    'settlement': f.settlement,
                    'occurred_at': f.occurred_at.isoformat(),
                    'occurred_ts': int(f.occurred_at.timestamp() * 1000),
                    'area_hectares': float(f.area_hectares or 0),
                    'fatalities_count': f.fatalities_count,
                    'cause_name': f.cause.name if f.cause else None,
                    'cause_category': f.cause.category if f.cause else None,
                    'commander': f.commander,
                },
                'geometry': json.loads(f.geo),
            })

        return Response({'type': 'FeatureCollection', 'features': features})


class DangerLayerView(APIView):
    """Слой пожароопасности: полигоны районов, окрашенные по классу на дату."""
    permission_classes = [AllowAny]

    def get(self, request):
        target_date = request.query_params.get('date')
        if target_date:
            try:
                target_date = date.fromisoformat(target_date)
            except ValueError:
                target_date = timezone.localdate()
        else:
            target_date = timezone.localdate()

        forecasts = (
            FireDangerForecast.objects
            .filter(date=target_date)
            .select_related('district')
            .annotate(geo=AsGeoJSON('district__geometry'))
        )

        features = []
        for f in forecasts:
            features.append({
                'type': 'Feature',
                'properties': {
                    'district_id': f.district_id,
                    'district_name': f.district.name,
                    'danger_class': f.danger_class,
                    'source': f.source,
                    'nesterov_index': float(f.nesterov_index) if f.nesterov_index else None,
                },
                'geometry': json.loads(f.geo),
            })

        return Response({
            'type': 'FeatureCollection',
            'features': features,
            'date': target_date.isoformat(),
        })


class FireCreateView(APIView):
    """
    Создание пожара кликом по карте.

    POST /api/fires/create/  (JSON):
      {
        "lat": 52.3, "lng": 104.3,
        "category": "forest" | "techno",
        "occurred_at": "2026-07-09T14:00",
        "settlement": "...", "area_hectares": 12.5,
        "fatalities_count": 0, "commander": "...", "cause_raw": "..."
      }

    Для простоты локального запуска эндпоинт открыт (без авторизации и без CSRF).
    Автор проставляется текущим пользователем, а если запрос анонимный —
    первым суперпользователем. Район определяется по координатам автоматически.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    @staticmethod
    def _num(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _int(value, default=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def post(self, request):
        data = request.data

        try:
            lat = float(data.get('lat'))
            lng = float(data.get('lng'))
        except (TypeError, ValueError):
            return Response({'detail': 'Некорректные координаты (lat/lng).'},
                            status=status.HTTP_400_BAD_REQUEST)

        category = data.get('category')
        if category not in ('forest', 'techno'):
            return Response({'detail': 'Категория должна быть forest или techno.'},
                            status=status.HTTP_400_BAD_REQUEST)

        occurred_raw = data.get('occurred_at')
        occurred_at = parse_datetime(occurred_raw) if occurred_raw else None
        if occurred_at is None:
            return Response({'detail': 'Укажите дату и время (occurred_at).'},
                            status=status.HTTP_400_BAD_REQUEST)
        if timezone.is_naive(occurred_at):
            occurred_at = timezone.make_aware(occurred_at, timezone.get_current_timezone())

        User = get_user_model()
        user = request.user if request.user.is_authenticated else None
        if user is None:
            user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if user is None:
            return Response(
                {'detail': 'Нет ни одного пользователя. Создайте суперпользователя: '
                           'docker compose exec backend python manage.py createsuperuser'},
                status=status.HTTP_400_BAD_REQUEST)

        point = Point(lng, lat, srid=4326)
        district = District.objects.filter(geometry__contains=point).first()

        fire = Fire.objects.create(
            category=category,
            location=point,
            settlement=(data.get('settlement') or '').strip(),
            occurred_at=occurred_at,
            area_hectares=self._num(data.get('area_hectares'), 0),
            fatalities_count=self._int(data.get('fatalities_count'), 0),
            commander=(data.get('commander') or '').strip(),
            cause_raw=(data.get('cause_raw') or '').strip(),
            district=district,
            created_by=user,
        )

        return Response({
            'type': 'Feature',
            'properties': {
                'id': fire.id,
                'category': fire.category,
                'settlement': fire.settlement,
                'occurred_at': fire.occurred_at.isoformat(),
                'occurred_ts': int(fire.occurred_at.timestamp() * 1000),
                'area_hectares': float(fire.area_hectares or 0),
                'fatalities_count': fire.fatalities_count,
                'cause_name': None,
                'cause_category': None,
                'commander': fire.commander,
                'district_name': district.name if district else None,
            },
            'geometry': {'type': 'Point', 'coordinates': [lng, lat]},
        }, status=status.HTTP_201_CREATED)