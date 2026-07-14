"""
Загружает границы районов Иркутской области из fires/data/irkutsk_districts.geojson
и справочник метеостанций.

Если файла нет — миграция не падает, просто выводит предупреждение.
Заполнить данные потом можно командой:
    python manage.py fetch_districts
    python manage.py loaddata initial_stations  (или напрямую в shell)
"""
import json
from pathlib import Path

from django.contrib.gis.geos import GEOSGeometry, Point, MultiPolygon, Polygon
from django.db import migrations


STATIONS = [
    ('irkutsk',      'Иркутск',       52.290, 104.290),
    ('bratsk',       'Братск',        56.140, 101.610),
    ('ust_ilimsk',   'Усть-Илимск',   58.000, 102.660),
    ('tulun',        'Тулун',         54.560, 100.580),
    ('kirensk',      'Киренск',       57.780, 108.120),
    ('bodaibo',      'Бодайбо',       57.850, 114.190),
    ('nizhneudinsk', 'Нижнеудинск',   54.900,  99.030),
    ('ust_kut',      'Усть-Кут',      56.790, 105.770),
    ('cheremhovo',   'Черемхово',     53.150, 103.070),
    ('erbogachen',   'Ербогачён',     61.280, 108.020),
    ('zhigalovo',    'Жигалово',      54.810, 105.160),
    ('bayandaevo',   'Баяндай',       53.010, 105.510),
]

DATA_FILE = Path(__file__).resolve().parent.parent / 'data' / 'irkutsk_districts.geojson'


def load_districts(apps, schema_editor):
    District = apps.get_model('fires', 'District')

    if not DATA_FILE.exists():
        print(f'\n[!] Файл {DATA_FILE} не найден.')
        print('    Запустите: python manage.py fetch_districts')
        print('    Затем повторите миграцию или загрузите данные вручную.')
        return

    with open(DATA_FILE, encoding='utf-8') as f:
        geojson = json.load(f)

    created = 0
    for feature in geojson.get('features', []):
        name = feature['properties'].get('name')
        if not name:
            continue
        geom = GEOSGeometry(json.dumps(feature['geometry']), srid=4326)
        # Всегда сохраняем как MultiPolygon
        if geom.geom_type == 'Polygon':
            geom = MultiPolygon(geom)
        District.objects.update_or_create(
            name=name,
            defaults={'geometry': geom},
        )
        created += 1
    print(f'\n[✓] Загружено районов: {created}')


def load_stations(apps, schema_editor):
    Station = apps.get_model('fires', 'WeatherStation')
    District = apps.get_model('fires', 'District')

    for code, name, lat, lon in STATIONS:
        # Пытаемся найти район, в котором стоит станция
        point = Point(lon, lat, srid=4326)
        district = None
        for d in District.objects.all():
            if d.geometry.contains(point):
                district = d
                break
        Station.objects.update_or_create(
            code=code,
            defaults={
                'name': name,
                'location': point,
                'district': district,
                'is_active': True,
            },
        )
    print(f'[✓] Загружено метеостанций: {len(STATIONS)}')


def unload(apps, schema_editor):
    apps.get_model('fires', 'WeatherStation').objects.all().delete()
    apps.get_model('fires', 'District').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('fires', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(load_districts, unload),
        migrations.RunPython(load_stations, migrations.RunPython.noop),
    ]
