import requests
from datetime import datetime
from decimal import Decimal

OPEN_METEO_URL = 'https://api.open-meteo.com/v1/forecast'


def fetch_station_observations(station, days_back=7):
    from ..models import DailyWeatherObservation

    r = requests.get(OPEN_METEO_URL, params={
        'latitude': station.location.y,
        'longitude': station.location.x,
        'hourly': 'temperature_2m,dew_point_2m,precipitation',
        'past_days': days_back,
        'forecast_days': 1,
        'timezone': 'Asia/Irkutsk',
    }, timeout=30)
    r.raise_for_status()
    data = r.json()

    times = data['hourly']['time']
    temps = data['hourly']['temperature_2m']
    dews = data['hourly']['dew_point_2m']
    precs = data['hourly']['precipitation']

    by_date = {}
    for i, ts_str in enumerate(times):
        dt = datetime.fromisoformat(ts_str)
        d = dt.date()
        entry = by_date.setdefault(
            d, {'t14': None, 'td14': None, 'prec': Decimal('0')}
        )
        if dt.hour == 14:
            entry['t14'] = temps[i]
            entry['td14'] = dews[i]
        if precs[i] is not None:
            entry['prec'] += Decimal(str(precs[i]))

    saved = 0
    for d, vals in by_date.items():
        DailyWeatherObservation.objects.update_or_create(
            station=station, date=d,
            defaults={
                'temperature_14': vals['t14'],
                'dew_point_14': vals['td14'],
                'precipitation_mm': vals['prec'],
            }
        )
        saved += 1
    return saved
