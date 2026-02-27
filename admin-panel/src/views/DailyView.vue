<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { ApiResponse, StockItem } from '../types'
import ToastNotify from '../components/ToastNotify.vue'
import AddToWatchlist from '../components/AddToWatchlist.vue'
import { useRouter } from 'vue-router'

const router = useRouter()

interface SystemStatus {
  scheduler_running: boolean
  today_recommendations: number
  email_configured: boolean
  last_update: string
  system_health: string
  trading_mode: string
}

interface DailyStock extends StockItem {
  id?: number
  date?: string
  status?: string
}

const status = ref<SystemStatus | null>(null)
const stocks = ref<DailyStock[]>([])
const dateFilter = ref(new Date().toISOString().slice(0, 10))
const loading = ref(false)
const analyzing = ref(false)
const toast = ref({ show: false, msg: '', type: 'info' })

function notify(msg: string, type = 'info') {
  toast.value = { show: true, msg, type }
  setTimeout(() => (toast.value.show = false), 3000)
}

const veryHigh = computed(() => stocks.value.filter(s => s.confidence === 'very_high'))
const high = computed(() => stocks.value.filter(s => s.confidence === 'high'))
const medium = computed(() => stocks.value.filter(s => s.confidence === 'medium'))
const avgScore = computed(() => {
  if (!stocks.value.length) return 0
  return stocks.value.reduce((s, x) => s + (x.total_score || 0), 0) / stocks.value.length
})
const markets = computed(() => [...new Set(stocks.value.map(s => s.market))])

async function loadStatus() {
  try {
    const res = await fetch('/api/daily/status')
    const data: ApiResponse<SystemStatus> = await res.json()
    if (data.success) status.value = data.data
  } catch { /* ignore */ }
}

async function loadRecommendations() {
  loading.value = true
  try {
    const res = await fetch(`/api/daily/recommendations?date=${dateFilter.value}&limit=50`)
    const data: ApiResponse<DailyStock[]> = await res.json()
    if (data.success) stocks.value = data.data
  } finally {
    loading.value = false
  }
}

async function runAnalysis() {
  analyzing.value = true
  notify('开始执行股票分析…', 'info')
  try {
    const res = await fetch('/api/daily/run_analysis', { method: 'POST' })
    const data = await res.json()
    if (data.success) {
      notify(data.message, 'success')
      await loadRecommendations()
      await loadStatus()
    } else {
      notify(data.message || '分析失败', 'error')
    }
  } finally {
    analyzing.value = false
  }
}

async function updateStockStatus(stockId: number, newStatus: string) {
  await fetch('/api/daily/update_status', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: stockId, status: newStatus }),
  })
  const s = stocks.value.find(x => x.id === stockId)
  if (s) s.status = newStatus
}

function goAnalyze(code: string) {
  router.push({ path: '/analyzer', query: { code } })
}

function confLabel(c: string) {
  return ({ very_high: '强烈推荐', high: '推荐', medium: '关注' } as Record<string, string>)[c] || c
}
function confCls(c: string) {
  if (c === 'very_high') return 'bg-green-100 text-green-800 border-green-200'
  if (c === 'high') return 'bg-blue-100 text-blue-800 border-blue-200'
  return 'bg-gray-100 text-gray-600 border-gray-200'
}
function statusOpts() {
  return [
    { value: 'pending', label: '待决策' },
    { value: 'bought', label: '已买入' },
    { value: 'watching', label: '观察中' },
    { value: 'ignored', label: '已忽略' },
  ]
}

onMounted(async () => {
  await Promise.all([loadStatus(), loadRecommendations()])
})
</script>

<template>
  <ToastNotify :show="toast.show" :message="toast.msg" :type="toast.type" />

  <div class="space-y-5">

    <!-- 系统状态卡片 -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-white rounded-xl border border-gray-200 p-5 text-center">
        <div class="text-3xl font-bold text-indigo-600">{{ status?.today_recommendations ?? '-' }}</div>
        <div class="text-xs text-gray-500 mt-1">今日推荐</div>
        <button @click="runAnalysis" :disabled="analyzing"
                class="mt-3 w-full text-xs px-3 py-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition">
          {{ analyzing ? '分析中…' : '立即分析' }}
        </button>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-5 text-center">
        <div class="text-3xl font-bold" :class="status?.scheduler_running ? 'text-green-600' : 'text-red-500'">
          {{ status?.scheduler_running ? 'ON' : 'OFF' }}
        </div>
        <div class="text-xs text-gray-500 mt-1">调度系统</div>
        <div class="mt-3 text-xs text-gray-400">{{ status?.scheduler_running ? '自动运行中' : '手动模式' }}</div>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-5 text-center">
        <div class="text-3xl font-bold" :class="status?.email_configured ? 'text-green-600' : 'text-amber-500'">
          {{ status?.email_configured ? '✓' : '✗' }}
        </div>
        <div class="text-xs text-gray-500 mt-1">邮件推送</div>
        <div class="mt-3 text-xs text-gray-400">{{ status?.email_configured ? '已配置' : '未配置' }}</div>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-5 text-center">
        <div class="text-lg font-bold text-gray-700 truncate">{{ status?.last_update ?? '-' }}</div>
        <div class="text-xs text-gray-500 mt-1">最后更新</div>
        <button @click="loadStatus(); loadRecommendations()"
                class="mt-3 w-full text-xs px-3 py-1.5 border border-gray-300 rounded-lg hover:bg-gray-50 transition">
          刷新
        </button>
      </div>
    </div>

    <!-- 日期选择 + 统计 -->
    <div class="bg-white rounded-xl border border-gray-200 p-5">
      <div class="flex flex-wrap items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <label class="text-sm font-medium text-gray-700">日期</label>
          <input type="date" v-model="dateFilter" @change="loadRecommendations()"
                 class="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
        </div>
        <div class="flex items-center gap-6 text-sm">
          <div class="text-center"><span class="text-xl font-bold text-indigo-600">{{ stocks.length }}</span><span class="text-gray-400 ml-1">推荐</span></div>
          <div class="text-center"><span class="text-xl font-bold text-green-600">{{ veryHigh.length }}</span><span class="text-gray-400 ml-1">强推</span></div>
          <div class="text-center"><span class="text-xl font-bold text-purple-600">{{ avgScore.toFixed(3) }}</span><span class="text-gray-400 ml-1">均分</span></div>
          <div class="text-center"><span class="text-xl font-bold text-amber-600">{{ markets.length }}</span><span class="text-gray-400 ml-1">板块</span></div>
        </div>
      </div>
    </div>

    <!-- 重点推荐 (very_high) -->
    <div v-if="veryHigh.length" class="space-y-3">
      <h3 class="text-sm font-semibold text-green-700 flex items-center gap-1">
        <span class="text-base">⭐</span> 重点关注 ({{ veryHigh.length }}只)
      </h3>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="s in veryHigh" :key="s.symbol"
             class="bg-white rounded-xl border-l-4 border-l-green-500 border border-gray-200 p-4 hover:shadow-md transition">
          <div class="flex justify-between items-start mb-3">
            <div>
              <div class="text-base font-bold text-gray-900">{{ s.symbol }}</div>
              <div class="text-sm text-gray-500">{{ s.stock_name }}</div>
            </div>
            <div class="text-right">
              <span class="inline-block text-xs font-bold text-white bg-indigo-600 px-2 py-0.5 rounded-full">{{ (s.total_score ?? 0).toFixed(3) }}</span>
              <div class="text-xs text-green-600 font-semibold mt-1">强烈推荐</div>
            </div>
          </div>
          <div class="flex justify-between items-center mb-3">
            <div class="text-xl font-bold text-gray-900">¥{{ (s.current_price ?? 0).toFixed(2) }}</div>
            <span class="text-xs px-2 py-0.5 bg-gray-100 rounded text-gray-600">{{ s.market }}</span>
          </div>
          <div class="grid grid-cols-3 gap-2 text-center text-xs mb-3">
            <div>
              <div class="text-gray-400">竞价</div>
              <div class="font-semibold" :class="(s.auction_ratio ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'">
                {{ (s.auction_ratio ?? 0) >= 0 ? '+' : '' }}{{ (s.auction_ratio ?? 0).toFixed(1) }}%
              </div>
            </div>
            <div>
              <div class="text-gray-400">目标</div>
              <div class="font-semibold text-red-600">¥{{ (s.target_price ?? 0).toFixed(2) }}</div>
            </div>
            <div>
              <div class="text-gray-400">止损</div>
              <div class="font-semibold text-green-600">¥{{ (s.stop_loss ?? 0).toFixed(2) }}</div>
            </div>
          </div>
          <p class="text-xs text-gray-500 bg-gray-50 p-2 rounded mb-3 leading-relaxed">{{ s.strategy }}</p>
          <div class="flex items-center gap-2">
            <AddToWatchlist :symbol="s.symbol" :stock-name="s.stock_name" :market="s.market" />
            <button @click="goAnalyze(s.symbol)" class="text-xs px-2 py-1 border border-gray-300 rounded-md hover:bg-gray-50 transition">分析</button>
            <select v-if="s.id" :value="s.status || 'pending'" @change="updateStockStatus(s.id!, ($event.target as HTMLSelectElement).value)"
                    class="ml-auto text-xs border border-gray-200 rounded px-1.5 py-0.5">
              <option v-for="o in statusOpts()" :key="o.value" :value="o.value">{{ o.label }}</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- 推荐 (high) -->
    <div v-if="high.length" class="space-y-3">
      <h3 class="text-sm font-semibold text-blue-700 flex items-center gap-1">
        <span class="text-base">📈</span> 值得关注 ({{ high.length }}只)
      </h3>
      <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-3">
        <div v-for="s in high" :key="s.symbol"
             class="bg-white rounded-xl border-l-4 border-l-blue-500 border border-gray-200 p-3 hover:shadow-sm transition">
          <div class="flex justify-between items-start mb-2">
            <div>
              <div class="text-sm font-bold text-gray-900">{{ s.symbol }}</div>
              <div class="text-xs text-gray-500">{{ s.stock_name }}</div>
            </div>
            <span class="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">{{ (s.total_score ?? 0).toFixed(3) }}</span>
          </div>
          <div class="flex justify-between items-center mb-2 text-sm">
            <span class="font-semibold">¥{{ (s.current_price ?? 0).toFixed(2) }}</span>
            <span class="text-xs" :class="(s.auction_ratio ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'">
              {{ (s.auction_ratio ?? 0) >= 0 ? '+' : '' }}{{ (s.auction_ratio ?? 0).toFixed(1) }}%
            </span>
          </div>
          <div class="flex items-center gap-2">
            <AddToWatchlist :symbol="s.symbol" :stock-name="s.stock_name" :market="s.market" />
            <button @click="goAnalyze(s.symbol)" class="text-xs px-2 py-1 border border-gray-300 rounded-md hover:bg-gray-50">分析</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 其他 (medium) -->
    <div v-if="medium.length" class="space-y-3">
      <h3 class="text-sm font-semibold text-gray-500 flex items-center gap-1">
        <span class="text-base">📊</span> 其他机会 ({{ medium.length }}只)
      </h3>
      <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
        <div v-for="s in medium" :key="s.symbol"
             class="bg-white rounded-lg border border-gray-200 p-2 text-center hover:shadow-sm transition cursor-pointer"
             @click="goAnalyze(s.symbol)">
          <div class="text-sm font-semibold text-gray-800">{{ s.symbol }}</div>
          <div class="text-xs text-gray-500 truncate">{{ s.stock_name }}</div>
          <div class="text-xs font-semibold mt-0.5">¥{{ (s.current_price ?? 0).toFixed(2) }}</div>
          <div class="text-xs" :class="(s.auction_ratio ?? 0) >= 0 ? 'text-red-500' : 'text-green-500'">
            {{ (s.auction_ratio ?? 0) >= 0 ? '+' : '' }}{{ (s.auction_ratio ?? 0).toFixed(1) }}%
          </div>
        </div>
      </div>
    </div>

    <!-- 全量表格 -->
    <div v-if="stocks.length" class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div class="px-5 py-4 border-b border-gray-200">
        <h3 class="text-sm font-semibold text-gray-700">全部推荐列表</h3>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-left">
            <tr>
              <th class="px-4 py-3 font-semibold text-gray-600">代码</th>
              <th class="px-4 py-3 font-semibold text-gray-600">名称</th>
              <th class="px-4 py-3 font-semibold text-gray-600">市场</th>
              <th class="px-4 py-3 font-semibold text-gray-600">价格</th>
              <th class="px-4 py-3 font-semibold text-gray-600">评分</th>
              <th class="px-4 py-3 font-semibold text-gray-600">竞价</th>
              <th class="px-4 py-3 font-semibold text-gray-600">信心</th>
              <th class="px-4 py-3 font-semibold text-gray-600">策略</th>
              <th class="px-4 py-3 font-semibold text-gray-600">状态</th>
              <th class="px-4 py-3 font-semibold text-gray-600">自选</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="s in stocks" :key="s.symbol" class="hover:bg-gray-50 transition">
              <td class="px-4 py-3 font-mono text-xs">{{ s.symbol }}</td>
              <td class="px-4 py-3 font-medium">{{ s.stock_name }}</td>
              <td class="px-4 py-3"><span class="text-xs px-2 py-0.5 bg-gray-100 rounded">{{ s.market }}</span></td>
              <td class="px-4 py-3 font-semibold">¥{{ (s.current_price ?? 0).toFixed(2) }}</td>
              <td class="px-4 py-3"><span class="text-xs text-white bg-indigo-600 px-2 py-0.5 rounded-full">{{ (s.total_score ?? 0).toFixed(3) }}</span></td>
              <td class="px-4 py-3" :class="(s.auction_ratio ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'">
                {{ (s.auction_ratio ?? 0) >= 0 ? '+' : '' }}{{ (s.auction_ratio ?? 0).toFixed(1) }}%
              </td>
              <td class="px-4 py-3"><span class="text-xs px-2 py-0.5 rounded border" :class="confCls(s.confidence)">{{ confLabel(s.confidence) }}</span></td>
              <td class="px-4 py-3 max-w-xs"><p class="text-xs text-gray-500 truncate">{{ s.strategy }}</p></td>
              <td class="px-4 py-3">
                <select v-if="s.id" :value="s.status || 'pending'" @change="updateStockStatus(s.id!, ($event.target as HTMLSelectElement).value)"
                        class="text-xs border border-gray-200 rounded px-1.5 py-0.5">
                  <option v-for="o in statusOpts()" :key="o.value" :value="o.value">{{ o.label }}</option>
                </select>
              </td>
              <td class="px-4 py-3"><AddToWatchlist :symbol="s.symbol" :stock-name="s.stock_name" :market="s.market" /></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!stocks.length && !loading" class="bg-white rounded-xl border border-gray-200 p-16 text-center text-gray-400">
      <svg class="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" stroke-width="1" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"/>
      </svg>
      <p class="text-sm mb-2">暂无推荐股票</p>
      <p class="text-xs mb-4">点击「立即分析」开始生成今日推荐</p>
      <button @click="runAnalysis" :disabled="analyzing"
              class="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition">
        {{ analyzing ? '分析中…' : '开始分析' }}
      </button>
    </div>
  </div>
</template>
