<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'

const props = defineProps({
  min: { type: Date, required: true },
  max: { type: Date, required: true },
})
const emit = defineEmits(['change'])

const DAY = 86400000

const totalDays = computed(() => Math.max(1, Math.ceil((props.max - props.min) / DAY)))
const fromDay = ref(0)
const toDay = ref(totalDays.value)
const playing = ref(false)
const windowSize = ref(7)
const speed = ref(400)

const fromDate = computed(() => new Date(props.min.getTime() + fromDay.value * DAY))
const toDate = computed(() => new Date(props.min.getTime() + toDay.value * DAY))

let timer = null

watch([fromDate, toDate], () => {
  emit('change', { from: fromDate.value, to: toDate.value })
}, { immediate: true })

function togglePlay() {
  playing.value = !playing.value
  if (playing.value) {
    // При старте: если "toDay" в конце, начинаем сначала
    if (toDay.value >= totalDays.value) {
      fromDay.value = 0
      toDay.value = windowSize.value
    } else {
      toDay.value = Math.min(fromDay.value + windowSize.value, totalDays.value)
    }
    timer = setInterval(step, speed.value)
  } else {
    clearInterval(timer)
    timer = null
  }
}

function step() {
  if (toDay.value >= totalDays.value) {
    clearInterval(timer)
    playing.value = false
    return
  }
  fromDay.value += 1
  toDay.value += 1
}

function fmt(d) {
  return d.toLocaleDateString('ru', { day: '2-digit', month: 'short', year: '2-digit' })
}

function onFromInput() {
  if (fromDay.value > toDay.value) toDay.value = fromDay.value
}
function onToInput() {
  if (toDay.value < fromDay.value) fromDay.value = toDay.value
}

onUnmounted(() => timer && clearInterval(timer))
</script>

<template>
  <div class="slider">
    <button class="play" @click="togglePlay">
      {{ playing ? '⏸' : '▶' }}
    </button>

    <div class="range-display">
      {{ fmt(fromDate) }} — {{ fmt(toDate) }}
    </div>

    <div class="dual">
      <input type="range" v-model.number="fromDay"
             :min="0" :max="totalDays" :disabled="playing"
             @input="onFromInput">
      <input type="range" v-model.number="toDay"
             :min="0" :max="totalDays" :disabled="playing"
             @input="onToInput">
    </div>

    <div class="controls">
      <label>
        Окно, дн.
        <input type="number" v-model.number="windowSize" min="1" max="60">
      </label>
      <label>
        Скорость
        <select v-model.number="speed">
          <option :value="800">×1</option>
          <option :value="400">×2</option>
          <option :value="200">×5</option>
          <option :value="80">×10</option>
        </select>
      </label>
    </div>
  </div>
</template>

<style scoped>
.slider {
  position: absolute;
  bottom: 12px;
  left: 12px;
  right: 12px;
  background: rgba(255, 255, 255, 0.97);
  padding: 10px 14px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 12px;
  align-items: center;
  z-index: 500;
}
.play {
  width: 40px; height: 40px; border-radius: 50%;
  background: #c62828; color: #fff; border: none;
  font-size: 18px; cursor: pointer;
}
.play:hover { background: #b71c1c; }
.range-display {
  font-family: monospace; font-size: 13px; color: #333;
  text-align: center; grid-column: 2; grid-row: 1;
}
.dual {
  position: relative; height: 24px;
  grid-column: 2; grid-row: 2;
}
.dual input {
  position: absolute; left: 0; right: 0; width: 100%;
  pointer-events: auto; background: transparent;
}
.controls { display: flex; gap: 10px; grid-column: 3; grid-row: 1 / span 2; }
.controls label {
  display: flex; flex-direction: column;
  font-size: 11px; color: #666; gap: 2px;
}
.controls input, .controls select {
  width: 60px; padding: 3px 6px;
  border: 1px solid #ddd; border-radius: 4px;
}
</style>
