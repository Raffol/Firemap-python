// Единый источник констант для карты и легенды.

export const IRKUTSK_CENTER = [104.29, 52.29] // [lon, lat]
export const IRKUTSK_ZOOM = 6

export const CATEGORY_LABELS = {
  forest: 'Лесной',
  techno: 'Техносферный',
}

export const CATEGORY_COLORS = {
  forest: '#2e7d32',
  techno: '#c62828',
}

export const DANGER_LABELS = {
  1: 'Отсутствует',
  2: 'Малая',
  3: 'Средняя',
  4: 'Высокая',
  5: 'Чрезвычайная',
}

export const DANGER_COLORS = {
  1: '#4caf50',
  2: '#cddc39',
  3: '#ffc107',
  4: '#ff9800',
  5: '#d32f2f',
}

export function formatArea(hectares) {
  const v = Number(hectares || 0)
  if (v >= 100) return `${(v / 100).toFixed(2)} км²`
  if (v >= 1) return `${v.toFixed(1)} га`
  return `${(v * 10000).toFixed(0)} м²`
}

export function formatDate(iso) {
  return new Date(iso).toLocaleString('ru', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}
