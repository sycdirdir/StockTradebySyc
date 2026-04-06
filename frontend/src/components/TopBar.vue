<template>
  <header class="top-bar">
    <div class="top-bar__brand">
      <div class="top-bar__logo">Q</div>
      <span class="top-bar__title">QuantView Pro</span>
      <span class="top-bar__version">v2.4.1</span>
    </div>
    <div class="top-bar__actions">
      <span class="toolbar-btn" @click="showToast('功能开发中')">🌙 深色</span>
      <span class="toolbar-btn" @click="toggleFullscreen">⛶ 全屏</span>
    </div>
  </header>
</template>

<script setup>
const emit = defineEmits(['toast'])

function showToast(msg) {
  emit('toast', msg)
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {})
  } else {
    document.exitFullscreen().catch(() => {})
  }
}
</script>
