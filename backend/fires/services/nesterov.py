from decimal import Decimal
from datetime import timedelta

RESET_PRECIPITATION_MM = Decimal('3.0')
LOOKBACK_DAYS = 60


def classify_nesterov(index_value):
    """Класс пожароопасности по значению индекса Нестерова."""
    v = float(index_value)
    if v <= 300:
        return 1
    if v <= 1000:
        return 2
    if v <= 4000:
        return 3
    if v <= 10000:
        return 4
    return 5


def compute_nesterov_for_station(station, target_date):
    """
    Индекс Нестерова для метеостанции на дату.
    КП = Σ(t * (t - td)) за дни без осадков.
    Осадки >= 3 мм обнуляют накопление.
    """
    from ..models import DailyWeatherObservation

    start_date = target_date - timedelta(days=LOOKBACK_DAYS)
    observations = list(
        DailyWeatherObservation.objects
        .filter(station=station, date__gte=start_date, date__lte=target_date)
        .order_by('date')
    )
    if not observations:
        return None

    index = Decimal('0')
    for obs in observations:
        if obs.precipitation_mm and obs.precipitation_mm >= RESET_PRECIPITATION_MM:
            index = Decimal('0')
            continue
        if obs.temperature_14 is None or obs.dew_point_14 is None:
            continue
        t = obs.temperature_14
        td = obs.dew_point_14
        if t <= 0:
            continue
        index += t * (t - td)
    return index


def compute_nesterov_for_district(district, target_date):
    """Индекс района = среднее по активным станциям района.
    Если своих нет — ближайшая станция."""
    from django.contrib.gis.db.models.functions import Distance
    from ..models import WeatherStation

    stations = list(district.weather_stations.filter(is_active=True))
    if not stations:
        centroid = district.geometry.centroid
        nearest = (
            WeatherStation.objects
            .filter(is_active=True)
            .annotate(dist=Distance('location', centroid))
            .order_by('dist')
            .first()
        )
        if not nearest:
            return None
        stations = [nearest]

    values = []
    for st in stations:
        v = compute_nesterov_for_station(st, target_date)
        if v is not None:
            values.append(v)
    if not values:
        return None
    return sum(values) / len(values)
