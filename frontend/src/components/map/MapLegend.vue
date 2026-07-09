<script setup>
import { CATEGORY_LABELS, CATEGORY_COLORS, DANGER_LABELS, DANGER_COLORS } from '@/composables/mapConfig'

defineProps({
  showFires: { type: Boolean, default: true },
  showDanger: { type: Boolean, default: true },
})
</script>

<template>
  <div class="legend">
    <div v-if="showFires" class="section">
      <div class="title">Пожары</div>
      <div class="row" v-for="(label, key) in CATEGORY_LABELS" :key="key">
        <span class="dot" :style="{ background: CATEGORY_COLORS[key] }"></span>
        <span>{{ label }}</span>
      </div>
    </div>
    <div v-if="showDanger" class="section">
      <div class="title">Класс пожароопасности</div>
      <div class="row" v-for="c in [1,2,3,4,5]" :key="c">
        <span class="chip" :style="{ background: DANGER_COLORS[c] }">{{ c }}</span>
        <span>{{ DANGER_LABELS[c] }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.legend {
  position: absolute;
  right: 12px;
  bottom: 90px;
  background: rgba(255, 255, 255, 0.95);
  padding: 12px 14px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  font-size: 12px;
  z-index: 500;
  max-width: 220px;
}
.section + .section { margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee; }
.title { font-weight: 600; margin-bottom: 6px; color: #333; }
.row { display: flex; align-items: center; gap: 8px; padding: 2px 0; color: #555; }
.dot { width: 12px; height: 12px; border-radius: 50%; opacity: 0.75; border: 1px solid #fff; box-shadow: 0 0 0 1px rgba(0,0,0,0.1); }
.chip { width: 22px; height: 18px; border-radius: 3px; text-align: center; font-size: 11px; font-weight: 600; color: #fff; line-height: 18px; }
</style>
