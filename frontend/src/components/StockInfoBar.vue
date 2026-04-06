<template>
  <div class="stock-info-bar">
    <div>
      <span class="stock-name">{{ stockInfo.name || '--' }}</span>
      <span class="stock-code">{{ stockInfo.ts_code || tsCode }}</span>
    </div>
    <div class="stock-divider"></div>
    <div>
      <span class="stock-price" :class="priceClass">{{ formatPrice(latest.close) }}</span>
      <span class="stock-change" :class="priceClass">{{ changeText }}</span>
    </div>
    <div class="stock-divider"></div>
    <div class="stock-stat">
      <span class="stock-stat__label">今开</span>
      <span class="stock-stat__value" :class="openClass">{{ formatPrice(latest.open) }}</span>
    </div>
    <div class="stock-stat">
      <span class="stock-stat__label">最高</span>
      <span class="stock-stat__value rise">{{ formatPrice(latest.high) }}</span>
    </div>
    <div class="stock-stat">
      <span class="stock-stat__label">最低</span>
      <span class="stock-stat__value fall">{{ formatPrice(latest.low) }}</span>
    </div>
    <div class="stock-stat">
      <span class="stock-stat__label">昨收</span>
      <span class="stock-stat__value">{{ formatPrice(latest.pre_close) }}</span>
    </div>
    <div class="stock-stat">
      <span class="stock-stat__label">成交量</span>
      <span class="stock-stat__value">{{ formatVol(latest.vol) }}</span>
    </div>
    <div class="stock-stat">
      <span class="stock-stat__label">成交额</span>
      <span class="stock-stat__value">{{ formatAmount(latest.amount) }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stockInfo: { type: Object, default: () => ({}) },
  tsCode: { type: String, default: '' },
  latest: { type: Object, default: () => ({}) },
})

const priceClass = computed(() => {
  const chg = props.latest.change
  if (chg > 0) return 'rise'
  if (chg < 0) return 'fall'
  return ''
})

const openClass = computed(() => {
  const o = props.latest.open
  const p = props.latest.pre_close
  if (!o || !p) return ''
  return o >= p ? 'rise' : 'fall'
})

const changeText = computed(() => {
  const { change, pct_chg } = props.latest
  if (!change && change !== 0) return ''
  const sign = change >= 0 ? '+' : ''
  return `${sign}${change.toFixed(2)} (${sign}${pct_chg.toFixed(2)}%)`
})

function formatPrice(v) {
  if (!v && v !== 0) return '--'
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatVol(v) {
  if (!v) return '--'
  const num = Number(v)
  if (num >= 10000) return (num / 10000).toFixed(2) + '万手'
  return num.toFixed(0) + '手'
}

function formatAmount(v) {
  if (!v) return '--'
  const num = Number(v)
  if (num >= 100000000) return (num / 100000000).toFixed(2) + '亿'
  if (num >= 10000) return (num / 10000).toFixed(2) + '万'
  return num.toFixed(0)
}
</script>
