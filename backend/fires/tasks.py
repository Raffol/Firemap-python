import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def refresh_station_weather(self, station_id):
    from .models import WeatherStation
    from .services.weather import fetch_station_observations

    try:
        station = WeatherStation.objects.get(pk=station_id, is_active=True)
    except WeatherStation.DoesNotExist:
        logger.warning(f'Станция {station_id} не найдена или неактивна')
        return {'skipped': True}

    try:
        saved = fetch_station_observations(station, days_back=7)
        return {'station': station.code, 'saved_days': saved}
    except Exception as exc:
        logger.exception(f'Ошибка загрузки погоды для {station.code}')
        raise self.retry(exc=exc)


@shared_task
def refresh_all_weather():
    from .models import WeatherStation
    ids = list(
        WeatherStation.objects
        .filter(is_active=True)
        .values_list('id', flat=True)
    )
    for sid in ids:
        refresh_station_weather.delay(sid)
    return {'scheduled': len(ids)}


@shared_task
def compute_nesterov_today():
    from .models import District, FireDangerForecast
    from .services.nesterov import compute_nesterov_for_district

    today = timezone.localdate()
    results = {'computed': 0, 'skipped_manual': 0, 'no_data': 0}

    for district in District.objects.all():
        existing = FireDangerForecast.objects.filter(
            district=district, date=today
        ).first()
        if existing and existing.source == 'manual':
            results['skipped_manual'] += 1
            continue

        index = compute_nesterov_for_district(district, today)
        if index is None:
            results['no_data'] += 1
            logger.warning(f'Нет данных: {district.name}')
            continue

        FireDangerForecast.set_from_nesterov(district, today, index)
        results['computed'] += 1

    logger.info(f'Nesterov compute: {results}')
    return results
