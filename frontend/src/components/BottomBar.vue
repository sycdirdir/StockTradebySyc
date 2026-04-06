<template>
  <footer class="bottom-bar">
    <div class="bottom-bar__left">
      <div class="status-indicator">
        <div class="status-indicator__dot" :style="{ background: connected ? 'var(--color-profit)' : 'var(--color-loss)' }"></div>
        <span>{{ connected ? '后端已连接' : '后端未连接' }}</span>
      </div>
      <span>数据延迟: 实时</span>
      <span>K线数量: {{ klineCount }}</span>
    </div>
    <div class="bottom-bar__right">
      <span>{{ periodLabel }}</span>
      <span>{{ currentTime }}</span>
    </div>
  </footer>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  connected: { type: Boolean, default: false },
  klineCount: { type: Number, default: 0 },
  period: { type: String, default: 'day' },
})

const currentTime = ref('')
let timer = null

const periodLabel = computed(() => {
  const map = {
    '1min': '1分钟线', '5min': '5分钟线', '15m': '15分钟线',
    '30min': '30分钟线', '60min': '60分钟线',
    'day': '日线', 'week': '周线', 'month': '月线',
  }
  return map[props.period] || props.period
})

function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: false,
  })
}

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>
