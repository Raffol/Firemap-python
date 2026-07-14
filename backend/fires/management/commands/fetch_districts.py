"""
Выгрузка полигонов муниципальных районов Иркутской области из OpenStreetMap.

Запускается ОДИН РАЗ вручную при обновлении справочника районов.
Результат кладётся в fires/data/irkutsk_districts.geojson и коммитится в git.
Data-миграция читает уже готовый файл — не тянет Overpass в рантайме.

Использование:
    python manage.py fetch_districts
    python manage.py fetch_districts --output custom/path.geojson
"""
import json
import time
from pathlib import Path

import requests
from django.core.management.base import BaseCommand

OVERPASS_URL = 'https://overpass-api.de/api/interpreter'

# Ищем муниципальные районы (admin_level=6) и городские округа,
# находящиеся внутри Иркутской области (relation с ISO3166-2:RU=RU-IRK).
OVERPASS_QUERY = """
[out:json][timeout:180];
area["ISO3166-2"="RU-IRK"]->.region;
(
  relation["admin_level"="6"]["boundary"="administrative"](area.region);
);
out geom;
"""

DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent.parent / 'data' / 'irkutsk_districts.geojson'


class Command(BaseCommand):
    help = 'Выгружает границы районов Иркутской области из OSM в GeoJSON.'

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, default=str(DEFAULT_OUTPUT))
        parser.add_argument('--timeout', type=int, default=180)

    def handle(self, *args, **opts):
        output = Path(opts['output'])
        output.parent.mkdir(parents=True, exist_ok=True)

        self.stdout.write(f'Запрос к Overpass API… (может занять до 3 минут)')
        t0 = time.time()

        r = requests.post(
            OVERPASS_URL,
            data={'data': OVERPASS_QUERY},
            timeout=opts['timeout'],
        )
        r.raise_for_status()
        data = r.json()

        elapsed = time.time() - t0
        self.stdout.write(f'Ответ получен за {elapsed:.1f} с, элементов: {len(data.get("elements", []))}')

        features = []
        for el in data.get('elements', []):
            if el.get('type') != 'relation':
                continue
            name = el.get('tags', {}).get('name')
            if not name:
                continue
            geometry = self._build_multipolygon(el)
            if geometry is None:
                self.stdout.write(self.style.WARNING(f'  Пропущен: {name} — не удалось собрать геометрию'))
                continue
            features.append({
                'type': 'Feature',
                'properties': {
                    'name': name,
                    'osm_id': el['id'],
                    'admin_level': el['tags'].get('admin_level'),
                    'okato': el['tags'].get('okato'),
                    'oktmo': el['tags'].get('oktmo'),
                },
                'geometry': geometry,
            })

        fc = {'type': 'FeatureCollection', 'features': features}
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(fc, f, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(
            f'Сохранено {len(features)} районов в {output}'
        ))

    def _build_multipolygon(self, relation):
        """
        Собирает MultiPolygon из members relation.
        Overpass возвращает 'way' с 'geometry' — списком точек.
        Кольца role='outer' складываются в отдельные полигоны,
        role='inner' — в дырки предыдущего outer.
        """
        outers = []
        inners = []
        for member in relation.get('members', []):
            if member.get('type') != 'way':
                continue
            geom = member.get('geometry')
            if not geom:
                continue
            ring = [(pt['lon'], pt['lat']) for pt in geom]
            if len(ring) < 4:
                continue
            # замкнуть кольцо, если не замкнуто
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            role = member.get('role', 'outer')
            if role == 'outer':
                outers.append(ring)
            elif role == 'inner':
                inners.append(ring)

        if not outers:
            return None

        # Простая сборка: каждое outer-кольцо = отдельный полигон,
        # inner-кольца прикрепляем к первому outer (для точности нужно
        # проверять вхождение, но для админ-границ достаточно).
        polygons = [[outer] for outer in outers]
        if inners and polygons:
            polygons[0].extend(inners)

        return {
            'type': 'MultiPolygon',
            'coordinates': [polygons[i] for i in range(len(polygons))],
        }
