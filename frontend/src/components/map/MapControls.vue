<script setup>
import { CATEGORY_LABELS } from '@/composables/mapConfig'

const props = defineProps({
  layers: { type: Object, required: true },       // { fires, danger, districts }
  filters: { type: Object, required: true },      // { category, date_from, date_to }
  loading: { type: Boolean, default: false },
  firesCount: { type: Number, default: 0 },
})
const emit = defineEmits(['update:layers', 'update:filters'])

function toggleLayer(key) {
  emit('update:layers', { ...props.layers, [key]: !props.layers[key] })
}
function updateFilter(key, value) {
  emit('update:filters', { ...props.filters, [key]: value })
}
</script>

<template>
  <div class="panel">
    <div class="header">
      <span>Слои и фильтры</span>
      <span v-if="loading" class="loading">…</span>
    </div>

    <div class="section">
      <div class="section-title">Слои</div>
      <label class="check">
        <input type="checkbox" :checked="layers.fires" @change="toggleLayer('fires')">
        Пожары <span class="count">({{ firesCount }})</span>
      </label>
      <label class="check">
        <input type="checkbox" :checked="layers.danger" @change="toggleLayer('danger')">
        Класс пожароопасности
      </label>
      <label class="check">
        <input type="checkbox" :checked="layers.districts" @change="toggleLayer('districts')">
        Границы районов
      </label>
    </div>

    <div class="section">
      <div class="section-title">Фильтры</div>
      <label class="field">
        <span>Категория</span>
        <select :value="filters.category"
                @change="updateFilter('category', $event.target.value)">
          <option value="">Все</option>
          <option v-for="(label, key) in CATEGORY_LABELS" :key="key" :value="key">
            {{ label }}
          </option>
        </select>
      </label>
      <label class="field">
        <span>С</span>
        <input type="date" :value="filters.date_from"
               @change="updateFilter('date_from', $event.target.value)">
      </label>
      <label class="field">
        <span>По</span>
        <input type="date" :value="filters.date_to"
               @change="updateFilter('date_to', $event.target.value)">
      </label>
    </div>
  </div>
</template>

<style scoped>
.panel {
  position: absolute;
  top: 12px;
  left: 12px;
  width: 250px;
  background: rgba(255, 255, 255, 0.97);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 500;
  overflow: hidden;
}
.header {
  padding: 10px 14px;
  background: #263238;
  color: #fff;
  font-weight: 500;
  font-size: 13px;
  display: flex; justify-content: space-between; align-items: center;
}
.loading { opacity: 0.7; }
.section { padding: 10px 14px; }
.section + .section { border-top: 1px solid #eee; }
.section-title { font-size: 11px; text-transform: uppercase;
                 letter-spacing: 0.5px; color: #888; margin-bottom: 8px; }
.check { display: flex; align-items: center; gap: 8px;
         padding: 4px 0; font-size: 13px; cursor: pointer; }
.count { color: #888; font-size: 12px; }
.field { display: flex; flex-direction: column; gap: 4px;
         margin-bottom: 8px; font-size: 12px; color: #555; }
.field select, .field input {
  padding: 5px 8px; border: 1px solid #ddd; border-radius: 4px;
  font-size: 13px;
}
</style>
