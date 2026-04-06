<template>
  <div class="chart-loading" v-if="loading">
    <div class="loading-spinner"></div>
    <span>加载中...</span>
  </div>
  <div ref="chartRef" style="width:100%;height:100%;"></div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  dates: { type: Array, default: () => [] },
  kline: { type: Array, default: () => [] },
  indicators: { type: Object, default: () => ({}) },
  signals: { type: Object, default: () => ({ buy_signals: [], sell_signals: [], hold_periods: [] }) },
  showMA: { type: Boolean, default: true },
  showBOLL: { type: Boolean, default: true },
  loading: { type: Boolean, default: false },
})

const chartRef = ref(null)
let chart = null

function buildOption() {
  const { dates, kline, indicators, signals } = props
  if (!dates.length || !kline.length) return {}

  // 买入/卖出标注
  const buyMarks = (signals.buy_signals || []).map(s => ({
    coord: [s.date, s.price],
    value: s.price,
    itemStyle: { color: '#f59e0b' },
    label: {
      show: true, formatter: 'B', fontSize: 11, fontWeight: 'bold',
      color: '#fff', backgroundColor: '#f59e0b', padding: [2, 5],
      borderRadius: 3, position: 'top', distance: 12,
    },
    symbol: 'triangle', symbolSize: 14, symbolRotate: 0, symbolOffset: [0, 8],
  }))

  const sellMarks = (signals.sell_signals || []).map(s => ({
    coord: [s.date, s.price],
    value: s.price,
    itemStyle: { color: '#3b82f6' },
    label: {
      show: true, formatter: 'S', fontSize: 11, fontWeight: 'bold',
      color: '#fff', backgroundColor: '#3b82f6', padding: [2, 5],
      borderRadius: 3, position: 'bottom', distance: 12,
    },
    symbol: 'triangle', symbolSize: 14, symbolRotate: 180, symbolOffset: [0, -8],
  }))

  // 持仓区间
  const holdPeriods = signals.hold_periods || []
  const holdAreas = []
  for (const hp of holdPeriods) {
    holdAreas.push([
      {
        xAxis: hp.start,
        itemStyle: {
          color: hp.is_profit ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)',
          borderColor: hp.is_profit ? 'rgba(34,197,94,0.25)' : 'rgba(239,68,68,0.25)',
          borderWidth: 1, borderType: 'dashed',
        },
        label: {
          show: true,
          formatter: `${hp.is_profit ? '🟢' : '🔴'} ${hp.is_profit ? '+' : ''}${hp.pnl}%`,
          position: 'insideTop', fontSize: 10,
          color: hp.is_profit ? '#22c55e' : '#ef4444',
          fontFamily: 'JetBrains Mono',
        },
      },
      { xAxis: hp.end },
    ])
  }

  // 成交量
  const volumes = kline.map(item => item[4])
  const volumeColors = kline.map(item =>
    item[1] >= item[0] ? 'rgba(239, 68, 68, 0.7)' : 'rgba(34, 197, 94, 0.7)'
  )

  // 买入/卖出信号的日期索引（用于 tooltip）
  const buyDateMap = {}
  ;(signals.buy_signals || []).forEach(s => { buyDateMap[s.date] = s })
  const sellDateMap = {}
  ;(signals.sell_signals || []).forEach(s => { sellDateMap[s.date] = s })

  const series = []

  series.push({
    name: 'K线', type: 'candlestick', xAxisIndex: 0, yAxisIndex: 0,
    data: kline,
    itemStyle: {
      color: '#ef4444', color0: '#22c55e',
      borderColor: '#ef4444', borderColor0: '#22c55e',
    },
    markPoint: { symbol: 'triangle', symbolSize: 14, data: [...buyMarks, ...sellMarks], animation: true },
    markArea: { silent: true, data: holdAreas },
  })

  if (props.showMA) {
    if (indicators.ma5) series.push({ name: 'MA5', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: indicators.ma5, smooth: 0.3, symbol: 'none', lineStyle: { width: 1.2, color: '#facc15', opacity: 0.85 } })
    if (indicators.ma10) series.push({ name: 'MA10', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: indicators.ma10, smooth: 0.3, symbol: 'none', lineStyle: { width: 1.2, color: '#a78bfa', opacity: 0.85 } })
    if (indicators.ma20) series.push({ name: 'MA20', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: indicators.ma20, smooth: 0.3, symbol: 'none', lineStyle: { width: 1.2, color: '#f472b6', opacity: 0.85 } })
  }

  if (props.showBOLL) {
    if (indicators.boll_upper) series.push({ name: 'BOLL上轨', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: indicators.boll_upper, symbol: 'none', lineStyle: { width: 1, color: '#06b6d4', type: 'dashed', opacity: 0.5 } })
    if (indicators.boll_mid) series.push({ name: 'BOLL中轨', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: indicators.boll_mid, symbol: 'none', lineStyle: { width: 1, color: '#06b6d4', opacity: 0.4 } })
    if (indicators.boll_lower) series.push({ name: 'BOLL下轨', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: indicators.boll_lower, symbol: 'none', lineStyle: { width: 1, color: '#06b6d4', type: 'dashed', opacity: 0.5 } })
  }

  series.push({
    name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1,
    data: volumes,
    itemStyle: { color: (params) => volumeColors[params.dataIndex] },
    barMaxWidth: 6,
  })

  return {
    backgroundColor: 'transparent',
    animation: true,
    animationDuration: 800,
    animationEasing: 'cubicOut',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', crossStyle: { color: '#64748b' }, lineStyle: { color: '#2a3650', type: 'dashed' } },
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      borderColor: '#2a3650', borderWidth: 1, padding: [12, 16],
      textStyle: { color: '#e2e8f0', fontSize: 12, fontFamily: 'JetBrains Mono, monospace' },
      formatter: function(params) {
        if (!params || !params.length) return ''
        const date = params[0].axisValue
        let html = `<div style="font-size:13px;font-weight:600;margin-bottom:8px;color:#e2e8f0">${date}</div>`
        params.forEach(p => {
          if (p.seriesName === 'K线') {
            const d = p.data
            const color = d[1] >= d[0] ? '#ef4444' : '#22c55e'
            const sign = d[1] >= d[0] ? '+' : ''
            const change = ((d[1] - d[0]) / d[0] * 100).toFixed(2)
            html += `<div style="display:grid;grid-template-columns:50px 1fr;gap:2px 12px;font-size:12px;margin-bottom:6px;padding-bottom:6px;border-bottom:1px solid #1e2a3a">
              <span style="color:#64748b">开盘</span><span style="color:${color}">${d[0].toFixed(2)}</span>
              <span style="color:#64748b">收盘</span><span style="color:${color}">${d[1].toFixed(2)}</span>
              <span style="color:#64748b">最低</span><span style="color:${color}">${d[2].toFixed(2)}</span>
              <span style="color:#64748b">最高</span><span style="color:${color}">${d[3].toFixed(2)}</span>
              <span style="color:#64748b">涨跌</span><span style="color:${color}">${sign}${change}%</span>
              <span style="color:#64748b">成交量</span><span style="color:#94a3b8">${(d[4] / 10000).toFixed(1)}万</span>
            </div>`
          } else if (p.value !== '-' && p.value !== null && p.value !== undefined) {
            html += `<div style="font-size:12px;display:flex;justify-content:space-between;gap:16px;"><span>${p.marker} ${p.seriesName}</span><span style="font-weight:500">${p.value}</span></div>`
          }
        })
        const currentDate = params[0].axisValue
        const buySig = buyDateMap[currentDate]
        const sellSig = sellDateMap[currentDate]
        if (buySig) html += `<div style="margin-top:6px;padding-top:6px;border-top:1px solid #1e2a3a;color:#f59e0b;font-weight:600;font-size:12px">▲ 买入信号 @ ¥${buySig.price.toFixed(2)}</div>`
        if (sellSig) html += `<div style="margin-top:6px;padding-top:6px;border-top:1px solid #1e2a3a;color:#3b82f6;font-weight:600;font-size:12px">▼ 卖出信号 @ ¥${sellSig.price.toFixed(2)}${sellSig.pnl ? ` (${sellSig.is_profit ? '+' : ''}${sellSig.pnl}%)` : ''}</div>`
        return html
      },
    },
    legend: { show: false },
    grid: [
      { left: 70, right: 30, top: 30, height: '52%' },
      { left: 70, right: 30, top: '70%', height: '18%' },
    ],
    xAxis: [
      {
        type: 'category', data: dates, gridIndex: 0,
        axisLine: { lineStyle: { color: '#1e2a3a' } }, axisTick: { show: false },
        axisLabel: { color: '#475569', fontSize: 10, fontFamily: 'JetBrains Mono, monospace', formatter: (val) => val.substring(5) },
        splitLine: { show: true, lineStyle: { color: '#1e2a3a', type: 'dashed' } },
        axisPointer: { show: true },
      },
      {
        type: 'category', data: dates, gridIndex: 1,
        axisLine: { lineStyle: { color: '#1e2a3a' } }, axisTick: { show: false },
        axisLabel: { color: '#475569', fontSize: 10, fontFamily: 'JetBrains Mono, monospace', formatter: (val) => val.substring(5) },
        splitLine: { show: false },
      },
    ],
    yAxis: [
      {
        type: 'value', gridIndex: 0, position: 'left', scale: true, splitNumber: 5,
        axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: '#64748b', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' },
        splitLine: { lineStyle: { color: '#1e2a3a', type: 'dashed' } },
      },
      {
        type: 'value', gridIndex: 1, position: 'left', scale: true, splitNumber: 3,
        axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: '#64748b', fontSize: 10, fontFamily: 'JetBrains Mono, monospace', formatter: (val) => (val / 10000).toFixed(0) + '万' },
        splitLine: { lineStyle: { color: '#1e2a3a', type: 'dashed' } },
      },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 50, end: 100 },
      {
        type: 'slider', xAxisIndex: [0, 1], bottom: 8, height: 20, start: 50, end: 100,
        borderColor: '#1e2a3a', backgroundColor: '#111827',
        fillerColor: 'rgba(59, 130, 246, 0.15)',
        handleStyle: { color: '#3b82f6', borderColor: '#3b82f6' },
        moveHandleStyle: { color: 'rgba(59, 130, 246, 0.3)' },
        textStyle: { color: '#64748b', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' },
        dataBackground: { lineStyle: { color: '#2a3650' }, areaStyle: { color: 'rgba(59, 130, 246, 0.05)' } },
        selectedDataBackground: { lineStyle: { color: '#3b82f6' }, areaStyle: { color: 'rgba(59, 130, 246, 0.1)' } },
      },
    ],
    series,
  }
}

function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value, null, { renderer: 'canvas' })
  const option = buildOption()
  if (option && Object.keys(option).length) chart.setOption(option)
}

function updateChart() {
  if (!chart) return
  const option = buildOption()
  if (option && Object.keys(option).length) chart.setOption(option, true)
}

function handleResize() {
  chart && chart.resize()
}

onMounted(() => {
  nextTick(() => {
    initChart()
    window.addEventListener('resize', handleResize)
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart && chart.dispose()
  chart = null
})

watch(
  () => [props.dates, props.kline, props.indicators, props.signals, props.showMA, props.showBOLL],
  () => updateChart(),
  { deep: true },
)

defineExpose({ chart, resize: handleResize })
</script>
