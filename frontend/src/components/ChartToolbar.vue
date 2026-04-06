<template>
  <div class="chart-toolbar">
    <!-- 股票搜索 -->
    <div class="stock-search">
      <input
        class="stock-search__input"
        type="text"
        placeholder="搜索股票代码/名称..."
        :value="keyword"
        @input="onInput($event.target.value)"
        @blur="hide"
        @focus="results.length && (showDropdown = true)"
      />
      <div class="stock-search__dropdown" v-if="showDropdown && results.length">
        <div
          class="stock-search__item"
          v-for="stock in results"
          :key="stock.ts_code"
          @mousedown.prevent="handleSelect(stock)"
        >
          <span class="stock-search__item-name">{{ stock.name }}</span>
          <span class="stock-search__item-code">{{ stock.ts_code }}</span>
        </div>
      </div>
    </div>

    <div class="toolbar-separator"></div>

    <!-- 周期切换 -->
    <div class="toolbar-group">
      <button
        class="toolbar-btn"
        :class="{ active: currentPeriod === p.value }"
        v-for="p in periods"
        :key="p.value"
        @click="$emit('update:currentPeriod', p.value)"
      >
        {{ p.label }}
      </button>
    </div>

    <div class="toolbar-separator"></div>

    <!-- 策略选择 -->
    <div class="toolbar-group">
      <span style="font-size:12px;color:var(--text-muted);margin-right:4px;">算法:</span>
      <select class="algo-select" :value="currentStrategy" @change="$emit('update:currentStrategy', $event.target.value)">
        <option value="macd_cross">MACD金叉死叉</option>
        <option value="ma_bounce">均线反弹策略</option>
        <option value="bollinger">布林带突破</option>
        <option value="kdj_rsi">KDJ+RSI组合</option>
      </select>
    </div>

    <div class="toolbar-separator"></div>

    <!-- 指标开关 -->
    <div class="toolbar-group">
      <button class="toolbar-btn" :class="{ active: showMA }" @click="$emit('update:showMA', !showMA)" title="均线">MA</button>
      <button class="toolbar-btn" :class="{ active: showBOLL }" @click="$emit('update:showBOLL', !showBOLL)" title="布林带">BOLL</button>
      <button class="toolbar-btn" :class="{ active: showVOL }" @click="$emit('update:showVOL', !showVOL)" title="成交量">VOL</button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  currentPeriod: { type: String, default: 'day' },
  currentStrategy: { type: String, default: 'macd_cross' },
  showMA: { type: Boolean, default: true },
  showBOLL: { type: Boolean, default: true },
  showVOL: { type: Boolean, default: true },
  keyword: { type: String, default: '' },
  results: { type: Array, default: () => [] },
  showDropdown: { type: Boolean, default: false },
})

const emit = defineEmits([
  'update:currentPeriod',
  'update:currentStrategy',
  'update:showMA',
  'update:showBOLL',
  'update:showVOL',
  'select-stock',
])

const periods = [
  { label: '1分', value: '1min' },
  { label: '5分', value: '5min' },
  { label: '15分', value: '15m' },
  { label: '30分', value: '30min' },
  { label: '60分', value: '60min' },
  { label: '日线', value: 'day' },
  { label: '周线', value: 'week' },
  { label: '月线', value: 'month' },
]

function onInput(val) {
  emit('search', val)
}

function hide() {
  setTimeout(() => emit('hide-dropdown'), 200)
}

function handleSelect(stock) {
  emit('select-stock', stock)
}
</script>
