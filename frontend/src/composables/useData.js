import { ref, watchEffect } from 'vue'
import { fetchKline, fetchStocks } from '../api'

/**
 * K 线数据 composable
 */
export function useKline(tsCode, period) {
  const klineData = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function load() {
    if (!tsCode.value) return
    loading.value = true
    error.value = null
    try {
      klineData.value = await fetchKline(tsCode.value, {
        period: period.value,
      })
    } catch (e) {
      error.value = e.message || '加载 K 线失败'
      console.error('K线加载失败:', e)
    } finally {
      loading.value = false
    }
  }

  watchEffect(load)

  return { klineData, loading, error, reload: load }
}

/**
 * 股票搜索 composable
 */
export function useStockSearch() {
  const keyword = ref('')
  const results = ref([])
  const showDropdown = ref(false)
  const searchTimer = ref(null)

  async function doSearch() {
    if (!keyword.value.trim()) {
      results.value = []
      showDropdown.value = false
      return
    }
    try {
      const res = await fetchStocks(keyword.value.trim(), 1, 20)
      results.value = res.data || []
      showDropdown.value = true
    } catch (e) {
      results.value = []
    }
  }

  function onInput(val) {
    keyword.value = val
    clearTimeout(searchTimer.value)
    searchTimer.value = setTimeout(doSearch, 300)
  }

  function select(stock) {
    keyword.value = stock.name
    showDropdown.value = false
    return stock
  }

  function hide() {
    setTimeout(() => { showDropdown.value = false }, 200)
  }

  return { keyword, results, showDropdown, onInput, select, hide }
}
