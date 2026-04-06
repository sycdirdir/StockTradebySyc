<template>
  <div class="app-layout">
    <!-- Toast -->
    <div class="toast" v-if="toastVisible" @animationend="toastVisible = false">{{ toastMsg }}</div>

    <!-- 顶部导航 -->
    <TopBar @toast="showToast" />

    <!-- 股票信息栏 -->
    <StockInfoBar
      :stock-info="stockInfo"
      :ts-code="currentTsCode"
      :latest="latestInfo"
    />

    <!-- 主内容 -->
    <div class="main-content">
      <!-- 图表面板 -->
      <div class="chart-panel">
        <!-- 工具栏 -->
        <ChartToolbar
          v-model:current-period="currentPeriod"
          v-model:current-strategy="currentStrategy"
          v-model:show-m-a="showMA"
          v-model:show-b-o-l-l="showBOLL"
          v-model:show-v-o-l="showVOL"
          :keyword="searchState.keyword"
          :results="searchState.results"
          :show-dropdown="searchState.showDropdown"
          @search="handleSearch"
          @select-stock="handleSelectStock"
          @hide-dropdown="searchState.showDropdown = false"
        />

        <!-- 图例 -->
        <LegendBar />

        <!-- 图表 -->
        <div class="chart-container">
          <KlineChart
            :dates="chartData?.dates || []"
            :kline="chartData?.kline || []"
            :indicators="chartData?.indicators || {}"
            :signals="chartData?.signals || { buy_signals: [], sell_signals: [], hold_periods: [] }"
            :show-m-a="showMA"
            :show-b-o-l-l="showBOLL"
            :loading="klineLoading"
          />
        </div>
      </div>

      <!-- 右侧面板 -->
      <SidePanel
        :stats="tradeStats"
        :signals="chartData?.signals || { buy_signals: [], sell_signals: [], hold_periods: [] }"
        :latest-price="latestInfo.close || 0"
      />
    </div>

    <!-- 底部状态栏 -->
    <BottomBar
      :connected="backendConnected"
      :kline-count="chartData?.count || 0"
      :period="currentPeriod"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import TopBar from './components/TopBar.vue'
import StockInfoBar from './components/StockInfoBar.vue'
import ChartToolbar from './components/ChartToolbar.vue'
import LegendBar from './components/LegendBar.vue'
import KlineChart from './components/KlineChart.vue'
import SidePanel from './components/SidePanel.vue'
import BottomBar from './components/BottomBar.vue'
import { fetchKline, fetchStockDetail, fetchStats, healthCheck } from './api'
import { useStockSearch } from './composables/useData'

// 状态
const currentTsCode = ref('600519.SH')
const currentPeriod = ref('day')
const currentStrategy = ref('macd_cross')
const showMA = ref(true)
const showBOLL = ref(true)
const showVOL = ref(true)

const chartData = ref(null)
const klineLoading = ref(false)
const stockInfo = ref({})
const latestInfo = ref({})
const tradeStats = ref({
  total_return: 0, max_drawdown: 0, trade_count: 0,
  win_rate: 0, profit_loss_ratio: 0, sharpe_ratio: 0,
  hold_days: 0, avg_hold_days: 0,
})
const backendConnected = ref(false)

// Toast
const toastVisible = ref(false)
const toastMsg = ref('')
function showToast(msg) {
  toastMsg.value = msg
  toastVisible.value = true
}

// 搜索
const searchState = useStockSearch()
function handleSearch(val) {
  searchState.onInput(val)
}
function handleSelectStock(stock) {
  searchState.select(stock)
  currentTsCode.value = stock.ts_code
  showToast(`已切换至 ${stock.name} (${stock.ts_code})`)
}

// 加载 K 线
async function loadKline() {
  klineLoading.value = true
  try {
    const data = await fetchKline(currentTsCode.value, { period: currentPeriod.value })
    chartData.value = data
    if (data.latest) latestInfo.value = data.latest
    loadStats()
  } catch (e) {
    console.error('K线加载失败:', e)
    chartData.value = null
  } finally {
    klineLoading.value = false
  }
}

// 加载股票信息
async function loadStockInfo() {
  try {
    const info = await fetchStockDetail(currentTsCode.value)
    stockInfo.value = info
  } catch (e) { /* 静默失败 */ }
}

// 加载统计
async function loadStats() {
  try {
    const stats = await fetchStats(currentTsCode.value, currentPeriod.value)
    tradeStats.value = stats
  } catch (e) { /* 静默失败 */ }
}

// 检查后端连接
async function checkHealth() {
  try {
    const res = await healthCheck()
    backendConnected.value = res.db === 'ok'
  } catch (e) {
    backendConnected.value = false
  }
}

// 监听股票代码和周期变化
watch([currentTsCode, currentPeriod], () => {
  loadKline()
  loadStockInfo()
})

onMounted(() => {
  checkHealth()
  loadKline()
  loadStockInfo()
})
</script>
