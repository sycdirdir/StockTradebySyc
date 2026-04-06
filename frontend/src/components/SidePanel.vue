<template>
  <aside class="side-panel">
    <!-- 策略表现 -->
    <div class="panel-section">
      <div class="panel-section__title">策略表现</div>
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-card__label">总收益率</div>
          <div class="stat-card__value" :class="stats.total_return >= 0 ? 'profit' : 'loss'">
            {{ stats.total_return >= 0 ? '+' : '' }}{{ stats.total_return }}%
          </div>
          <div class="stat-card__sub">{{ stats.total_return >= 0 ? '↑' : '↓' }} 运行收益</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__label">最大回撤</div>
          <div class="stat-card__value loss">-{{ Math.abs(stats.max_drawdown) }}%</div>
          <div class="stat-card__sub">风险控制</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__label">交易次数</div>
          <div class="stat-card__value accent">{{ stats.trade_count }}</div>
          <div class="stat-card__sub">胜率 {{ stats.win_rate }}%</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__label">持仓天数</div>
          <div class="stat-card__value">{{ stats.hold_days }}</div>
          <div class="stat-card__sub">平均 {{ stats.avg_hold_days }} 天/笔</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__label">盈亏比</div>
          <div class="stat-card__value" :class="stats.profit_loss_ratio >= 1 ? 'profit' : 'loss'">
            {{ stats.profit_loss_ratio }}
          </div>
          <div class="stat-card__sub">平均盈利 / 亏损</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__label">夏普比率</div>
          <div class="stat-card__value accent">{{ stats.sharpe_ratio }}</div>
          <div class="stat-card__sub">年化</div>
        </div>
      </div>
    </div>

    <!-- 当前持仓 -->
    <div class="panel-section">
      <div class="panel-section__title">当前持仓</div>
      <div class="position-card">
        <div class="position-row">
          <span class="position-row__label">状态</span>
          <span class="position-status" :class="position.isHolding ? 'holding' : 'closed'">
            <span class="status-dot" v-if="position.isHolding"></span>
            {{ position.isHolding ? '持仓中' : '已清仓' }}
          </span>
        </div>
        <div class="position-row">
          <span class="position-row__label">买入价格</span>
          <span class="position-row__value">¥{{ position.buyPrice }}</span>
        </div>
        <div class="position-row">
          <span class="position-row__label">当前价格</span>
          <span class="position-row__value" :style="{ color: position.pnl >= 0 ? 'var(--color-rise)' : 'var(--color-fall)' }">
            ¥{{ position.currentPrice }}
          </span>
        </div>
        <div class="position-row">
          <span class="position-row__label">持仓天数</span>
          <span class="position-row__value">{{ position.holdDays }} 天</span>
        </div>
        <div class="position-row">
          <span class="position-row__label">浮动盈亏</span>
          <span class="position-row__value" :class="position.pnl >= 0 ? 'profit' : 'loss'">
            {{ position.pnl >= 0 ? '+' : '' }}¥{{ position.pnlAmount }} ({{ position.pnl >= 0 ? '+' : '' }}{{ position.pnl }}%)
          </span>
        </div>
      </div>
    </div>

    <!-- 交易记录 -->
    <div class="panel-section" style="flex:1;overflow-y:auto;border-bottom:none;">
      <div class="panel-section__title">近期交易记录</div>
      <div class="trade-list">
        <div class="trade-item" v-for="(trade, idx) in tradeList" :key="idx">
          <div class="trade-item__indicator" :class="trade.type">
            {{ trade.type === 'buy' ? 'B' : 'S' }}
          </div>
          <div class="trade-item__info">
            <div class="trade-item__price">¥{{ trade.price }}</div>
            <div class="trade-item__date">{{ trade.date }} {{ trade.type === 'buy' ? '买入' : '卖出' }}</div>
          </div>
          <div class="trade-item__pnl">
            <div class="trade-item__pnl-value" :class="trade.pnlClass">{{ trade.pnlText }}</div>
            <div class="trade-item__pnl-pct">{{ trade.subText }}</div>
          </div>
        </div>
        <div v-if="!tradeList.length" style="text-align:center;color:var(--text-muted);padding:20px;font-size:13px;">
          暂无交易记录
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stats: { type: Object, default: () => ({ total_return: 0, max_drawdown: 0, trade_count: 0, win_rate: 0, profit_loss_ratio: 0, sharpe_ratio: 0, hold_days: 0, avg_hold_days: 0 }) },
  signals: { type: Object, default: () => ({ buy_signals: [], sell_signals: [], hold_periods: [] }) },
  latestPrice: { type: Number, default: 0 },
})

const position = computed(() => {
  const buys = props.signals.buy_signals || []
  const sells = props.signals.sell_signals || []
  if (!buys.length) return { isHolding: false, buyPrice: '--', currentPrice: '--', holdDays: 0, pnl: 0, pnlAmount: 0 }

  const lastBuy = buys[buys.length - 1]
  const lastSell = sells.length ? sells[sells.length - 1] : null

  // 如果最后一个操作的日期比最后买入的日期大，说明已清仓
  const isHolding = !lastSell || lastBuy.date > lastSell.date

  if (!isHolding) {
    return { isHolding: false, buyPrice: lastBuy.price.toFixed(2), currentPrice: lastSell.price.toFixed(2), holdDays: 0, pnl: 0, pnlAmount: 0 }
  }

  const buyPrice = lastBuy.price
  const currentPrice = props.latestPrice || buyPrice
  const pnl = currentPrice > buyPrice ? ((currentPrice - buyPrice) / buyPrice * 100).toFixed(2) : 0
  const pnlAmount = (currentPrice - buyPrice).toFixed(2)

  return {
    isHolding: true,
    buyPrice: buyPrice.toFixed(2),
    currentPrice: currentPrice.toFixed(2),
    holdDays: 5,
    pnl: Number(pnl),
    pnlAmount: Number(pnlAmount),
  }
})

const tradeList = computed(() => {
  const buys = (props.signals.buy_signals || []).slice(-10).reverse()
  const sells = (props.signals.sell_signals || []).slice(-10).reverse()
  const all = []
  for (const s of sells) {
    all.push({
      type: 'sell',
      price: s.price.toFixed(2),
      date: s.date ? s.date.substring(0, 10) : '--',
      pnlClass: s.is_profit ? 'profit' : 'loss',
      pnlText: `${s.is_profit ? '+' : ''}${s.pnl}%`,
      subText: s.is_profit ? '盈利' : '亏损',
    })
  }
  for (const b of buys) {
    all.push({
      type: 'buy',
      price: b.price.toFixed(2),
      date: b.date ? b.date.substring(0, 10) : '--',
      pnlClass: '',
      pnlText: '--',
      subText: '已买入',
    })
  }
  // 按日期倒序
  all.sort((a, b) => b.date.localeCompare(a.date))
  return all.slice(0, 20)
})
</script>
