<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'

import MapControls from '@/components/map/MapControls.vue'
import MapLegend from '@/components/map/MapLegend.vue'
import TimeSlider from '@/components/map/TimeSlider.vue'
import {
  IRKUTSK_CENTER, IRKUTSK_ZOOM,
  DANGER_COLORS, CATEGORY_COLORS, CATEGORY_LABELS,
  formatArea, formatDate,
} from '@/composables/mapConfig'

// --- Состояние ---
const mapContainer = ref(null)
let map = null
let popup = null

const layers = ref({ fires: true, danger: true, districts: false })
const filters = ref({
  category: '',
  date_from: '2026-05-01',
  date_to: '2026-09-30',
})
const timeRange = ref(null)  // {from, to} — от слайдера
const loading = ref(false)
const firesData = ref({ type: 'FeatureCollection', features: [] })

// Слайдер работает в пределах текущего фильтра date_from..date_to
const sliderMin = computed(() => new Date(filters.value.date_from))
const sliderMax = computed(() => new Date(filters.value.date_to))
const firesCount = computed(() => {
  if (!timeRange.value) return firesData.value.features.length
  const from = timeRange.value.from.getTime()
  const to = timeRange.value.to.getTime()
  return firesData.value.features.filter(
    f => f.properties.occurred_ts >= from && f.properties.occurred_ts <= to
  ).length
})

// --- Стиль базовой карты ---
// Простой растровый OSM для старта. Заменить на MapTiler / свой TileServer позже.
const BASE_STYLE = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '© OpenStreetMap contributors',
    },
  },
  layers: [
    { id: 'osm', type: 'raster', source: 'osm' },
  ],
}

// --- Инициализация карты ---
onMounted(() => {
  map = new maplibregl.Map({
    container: mapContainer.value,
    style: BASE_STYLE,
    center: IRKUTSK_CENTER,
    zoom: IRKUTSK_ZOOM,
    attributionControl: true,
  })
  map.addControl(new maplibregl.NavigationControl(), 'top-right')
  popup = new maplibregl.Popup({ closeButton: true, closeOnClick: true })

  map.on('load', async () => {
    addSourcesAndLayers()
    await Promise.all([loadDistricts(), loadDanger(), loadFires()])
    applyLayerVisibility()
    bindInteractions()
  })
})

onUnmounted(() => map && map.remove())

// --- Добавление источников и слоёв ---
function addSourcesAndLayers() {
  // 1. Границы районов
  map.addSource('districts', { type: 'geojson', data: emptyFC() })
  map.addLayer({
    id: 'districts-outline',
    type: 'line',
    source: 'districts',
    paint: { 'line-color': '#37474f', 'line-width': 1, 'line-opacity': 0.5 },
  })

  // 2. Слой пожароопасности (заливка полигонов)
  map.addSource('danger', { type: 'geojson', data: emptyFC() })
  map.addLayer({
    id: 'danger-fill',
    type: 'fill',
    source: 'danger',
    paint: {
      'fill-color': [
        'match', ['get', 'danger_class'],
        1, DANGER_COLORS[1], 2, DANGER_COLORS[2], 3, DANGER_COLORS[3],
        4, DANGER_COLORS[4], 5, DANGER_COLORS[5], '#e0e0e0',
      ],
      'fill-opacity': 0.35,
    },
  })
  map.addLayer({
    id: 'danger-outline',
    type: 'line',
    source: 'danger',
    paint: { 'line-color': '#546e7a', 'line-width': 0.5 },
  })

  // 3. Пожары — с кластеризацией
  map.addSource('fires', {
    type: 'geojson',
    data: emptyFC(),
    cluster: true,
    clusterMaxZoom: 12,
    clusterRadius: 50,
    clusterProperties: {
      forest_count: ['+', ['case', ['==', ['get', 'category'], 'forest'], 1, 0]],
      techno_count: ['+', ['case', ['==', ['get', 'category'], 'techno'], 1, 0]],
      total_area: ['+', ['get', 'area_hectares']],
      total_fatalities: ['+', ['get', 'fatalities_count']],
    },
  })

  // Кружок кластера
  map.addLayer({
    id: 'fires-clusters',
    type: 'circle',
    source: 'fires',
    filter: ['has', 'point_count'],
    paint: {
      'circle-color': [
        'step', ['get', 'point_count'],
        '#ffa726', 10, '#ef6c00', 50, '#b71c1c',
      ],
      'circle-radius': [
        'step', ['get', 'point_count'],
        18, 10, 24, 50, 32,
      ],
      'circle-stroke-width': 2,
      'circle-stroke-color': '#fff',
    },
  })

  // Число в кластере
  map.addLayer({
    id: 'fires-clusters-count',
    type: 'symbol',
    source: 'fires',
    filter: ['has', 'point_count'],
    layout: {
      'text-field': '{point_count_abbreviated}',
      'text-size': 13,
    },
    paint: { 'text-color': '#fff' },
  })

  // Отдельные точки
  map.addLayer({
    id: 'fires-point',
    type: 'circle',
    source: 'fires',
    filter: ['!', ['has', 'point_count']],
    paint: {
      'circle-radius': [
        'interpolate', ['linear'], ['get', 'area_hectares'],
        0, 5, 100, 9, 10000, 18,
      ],
      'circle-color': [
        'match', ['get', 'category'],
        'forest', CATEGORY_COLORS.forest,
        'techno', CATEGORY_COLORS.techno,
        '#888',
      ],
      'circle-opacity': 0.8,
      'circle-stroke-width': 1.5,
      'circle-stroke-color': '#fff',
    },
  })
}

// --- Загрузка данных ---
async function loadDistricts() {
  try {
    const r = await fetch('/api/districts/')
    const data = await r.json()
    map.getSource('districts').setData(data)
  } catch (e) {
    console.warn('Не удалось загрузить районы:', e)
  }
}

async function loadDanger() {
  try {
    const date = filters.value.date_to || new Date().toISOString().slice(0, 10)
    const r = await fetch(`/api/danger-layer/?date=${date}`)
    const data = await r.json()
    map.getSource('danger').setData(data)
  } catch (e) {
    console.warn('Не удалось загрузить пожароопасность:', e)
  }
}

async function loadFires() {
  loading.value = true
  try {
    const params = new URLSearchParams({
      date_from: filters.value.date_from,
      date_to: filters.value.date_to,
    })
    if (filters.value.category) params.append('category', filters.value.category)
    const r = await fetch(`/api/fires/?${params}`)
    const data = await r.json()
    firesData.value = data
    applyTimeFilter()  // сразу применяем текущий срез слайдера
  } catch (e) {
    console.warn('Не удалось загрузить пожары:', e)
  } finally {
    loading.value = false
  }
}

// --- Фильтрация по времени (клиентская) ---
function applyTimeFilter() {
  if (!map || !map.getSource('fires')) return
  if (!timeRange.value) {
    map.getSource('fires').setData(firesData.value)
    return
  }
  const from = timeRange.value.from.getTime()
  const to = timeRange.value.to.getTime()
  const filtered = {
    type: 'FeatureCollection',
    features: firesData.value.features.filter(
      f => f.properties.occurred_ts >= from && f.properties.occurred_ts <= to
    ),
  }
  map.getSource('fires').setData(filtered)
}

// --- Видимость слоёв ---
function applyLayerVisibility() {
  if (!map) return
  const set = (id, visible) =>
    map.getLayer(id) && map.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none')
  set('districts-outline', layers.value.districts)
  set('danger-fill', layers.value.danger)
  set('danger-outline', layers.value.danger)
  set('fires-clusters', layers.value.fires)
  set('fires-clusters-count', layers.value.fires)
  set('fires-point', layers.value.fires)
}

// --- Взаимодействия: клики, popup ---
function bindInteractions() {
  // Клик по кластеру — зумимся внутрь
  map.on('click', 'fires-clusters', (e) => {
    const feature = e.features[0]
    const clusterId = feature.properties.cluster_id
    map.getSource('fires').getClusterExpansionZoom(clusterId, (err, zoom) => {
      if (err) return
      map.easeTo({ center: feature.geometry.coordinates, zoom })
    })
  })

  // Наведение на кластер — тултип
  map.on('mouseenter', 'fires-clusters', (e) => {
    map.getCanvas().style.cursor = 'pointer'
    const p = e.features[0].properties
    popup.setLngLat(e.lngLat).setHTML(`
      <div style="font-size:12px">
        <div><b>${p.point_count} пожаров</b></div>
        <div>Лесных: ${p.forest_count}, техно: ${p.techno_count}</div>
        <div>Площадь: ${formatArea(p.total_area)}</div>
        <div>Погибших: ${p.total_fatalities}</div>
      </div>
    `).addTo(map)
  })
  map.on('mouseleave', 'fires-clusters', () => {
    map.getCanvas().style.cursor = ''
    popup.remove()
  })

  // Клик по точке — карточка
  map.on('click', 'fires-point', (e) => {
    const f = e.features[0]
    const p = f.properties
    popup.setLngLat(f.geometry.coordinates).setHTML(`
      <div class="fire-popup">
        <div class="cat cat-${p.category}">
          ${CATEGORY_LABELS[p.category] || p.category}
        </div>
        <h4>${p.settlement || 'Пожар'}</h4>
        <div class="row"><span>Дата:</span> ${formatDate(p.occurred_at)}</div>
        <div class="row"><span>Площадь:</span> ${formatArea(p.area_hectares)}</div>
        ${p.fatalities_count > 0 ? `<div class="row danger"><span>Погибших:</span> ${p.fatalities_count}</div>` : ''}
        ${p.cause_name ? `<div class="row"><span>Причина:</span> ${p.cause_name}</div>` : ''}
        ${p.commander ? `<div class="row"><span>Руководитель:</span> ${p.commander}</div>` : ''}
      </div>
    `).addTo(map)
  })
  map.on('mouseenter', 'fires-point', () => map.getCanvas().style.cursor = 'pointer')
  map.on('mouseleave', 'fires-point', () => map.getCanvas().style.cursor = '')

  // Клик по полигону опасности — показать класс
  map.on('click', 'danger-fill', (e) => {
    const p = e.features[0].properties
    const cls = p.danger_class
    popup.setLngLat(e.lngLat).setHTML(`
      <div style="font-size:13px">
        <b>${p.district_name}</b><br>
        Класс: <span style="background:${DANGER_COLORS[cls]};padding:2px 8px;color:#fff;border-radius:3px">${cls}</span>
        <div style="color:#888;font-size:11px;margin-top:4px">
          ${p.source === 'manual' ? 'Ручной ввод' : `Расчёт (индекс ${p.nesterov_index?.toFixed(0)})`}
        </div>
      </div>
    `).addTo(map)
  })
}

function emptyFC() { return { type: 'FeatureCollection', features: [] } }

// --- Реакции на изменение состояния ---
watch(layers, applyLayerVisibility, { deep: true })
watch(filters, async () => {
  await loadFires()
  await loadDanger()
}, { deep: true })
watch(timeRange, applyTimeFilter, { deep: true })
</script>

<template>
  <div class="map-view">
    <div ref="mapContainer" class="map"></div>

    <MapControls
      :layers="layers"
      :filters="filters"
      :loading="loading"
      :fires-count="firesCount"
      @update:layers="layers = $event"
      @update:filters="filters = $event"
    />

    <MapLegend
      :show-fires="layers.fires"
      :show-danger="layers.danger"
    />

    <TimeSlider
      :min="sliderMin"
      :max="sliderMax"
      @change="timeRange = $event"
    />
  </div>
</template>

<style scoped>
.map-view { position: relative; width: 100%; height: 100vh; }
.map { position: absolute; inset: 0; }
</style>

<style>
/* Стили popup — глобально, чтобы MapLibre их видел */
.maplibregl-popup-content .fire-popup { font-size: 12px; min-width: 200px; }
.maplibregl-popup-content .fire-popup h4 {
  margin: 4px 0 8px; font-size: 14px;
}
.maplibregl-popup-content .fire-popup .cat {
  display: inline-block; padding: 2px 8px; border-radius: 3px;
  font-size: 10px; text-transform: uppercase; color: #fff; margin-bottom: 4px;
}
.maplibregl-popup-content .fire-popup .cat-forest { background: #2e7d32; }
.maplibregl-popup-content .fire-popup .cat-techno { background: #c62828; }
.maplibregl-popup-content .fire-popup .row {
  padding: 2px 0; color: #555;
}
.maplibregl-popup-content .fire-popup .row span { color: #888; }
.maplibregl-popup-content .fire-popup .row.danger { color: #c62828; font-weight: 500; }
</style>
