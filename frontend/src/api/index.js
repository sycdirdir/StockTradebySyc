import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

/* 股票列表（搜索 + 分页） */
export async function fetchStocks(keyword = '', page = 1, pageSize = 20) {
  const { data } = await api.get('/stocks', {
    params: { keyword, page, page_size: pageSize },
  })
  return data
}

/* 股票详情 */
export async function fetchStockDetail(tsCode) {
  const { data } = await api.get(`/stocks/${tsCode}`)
  return data
}

/* K 线数据 */
export async function fetchKline(tsCode, { period = 'day', startDate = '', endDate = '', indicators = 'ma,boll' } = {}) {
  const { data } = await api.get(`/kline/${tsCode}`, {
    params: { period, start_date: startDate, end_date: endDate, indicators },
  })
  return data
}

/* 策略列表 */
export async function fetchStrategies() {
  const { data } = await api.get('/strategies')
  return data
}

/* 交易统计 */
export async function fetchStats(tsCode, period = 'day') {
  const { data } = await api.get('/stats', {
    params: { ts_code: tsCode, period },
  })
  return data
}

/* 健康检查 */
export async function healthCheck() {
  const { data } = await api.get('/health')
  return data
}
