<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import type { ApiResponse, StockItem } from '../types'
import ToastNotify from '../components/ToastNotify.vue'
import AddToWatchlist from '../components/AddToWatchlist.vue'
import { useRouter } from 'vue-router'

const router = useRouter()

interface SystemStatus {
  scheduler_running: boolean
  today_recommendations: number
  last_update: string
  system_health: string
  trading_mode: string
}

interface DailyStock extends StockItem {
  id?: number
  date?: string
  status?: string
}

/** 分析任务项 */
interface AnalysisTask {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  total: number
  current_stock: { symbol: string; name: string } | null
  message: string
  phase: string
  result?: { count: number; date: string }
  error?: string
  created_at: string
}

const status = ref<SystemStatus | null>(null)
const stocks = ref<DailyStock[]>([])
const dateFilter = ref(new Date().toISOString().slice(0, 10))
const loading = ref(false)
const analyzing = ref(false)
const toast = ref({ show: false, msg: '', type: 'info' })
const analysisQueue = ref<AnalysisTask[]>([])
const screenerRecords = ref<{ id: number; name: string; result_count: number; created_at: string }[]>([])
const applyingFromScreener = ref(false)
const showScreenerImport = ref(false)
let queuePollTimer: ReturnType<typeof setInterval> | null = null

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

/** 是否有运行中的分析任务 */
const hasRunningTask = computed(() => analysisQueue.value.some(t => t.status === 'pending' || t.status === 'running'))

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

/** 加载分析任务队列 */
async function loadAnalysisQueue() {
  try {
    const res = await fetch('/api/daily/analysis_queue?limit=10')
    const data: ApiResponse<{ tasks: AnalysisTask[] }> = await res.json()
    if (data.success) analysisQueue.value = data.data.tasks
  } catch { /* ignore */ }
}

/** 启动队列轮询（有运行中任务时） */
function startQueuePolling() {
  if (queuePollTimer) return
  queuePollTimer = setInterval(async () => {
    const hadRunning = hasRunningTask.value
    await loadAnalysisQueue()
    if (hadRunning && !hasRunningTask.value) {
      await onTaskCompleted()
    }
    if (!hasRunningTask.value && queuePollTimer) {
      clearInterval(queuePollTimer)
      queuePollTimer = null
    }
  }, 1500)
}

/** 停止队列轮询 */
function stopQueuePolling() {
  if (queuePollTimer) {
    clearInterval(queuePollTimer)
    queuePollTimer = null
  }
}

async function runAnalysis() {
  analyzing.value = true
  notify('开始执行股票分析…', 'info')
  try {
    const res = await fetch('/api/daily/run_analysis', { method: 'POST' })
    const data = await res.json()
    if (data.success && data.data?.task_id) {
      notify('分析任务已加入队列', 'info')
      await loadAnalysisQueue()
      startQueuePolling()
    } else if (data.success) {
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

/** 任务完成时刷新推荐列表 */
async function onTaskCompleted() {
  await loadRecommendations()
  await loadStatus()
}

/** 加载条件选股记录 */
async function loadScreenerRecords() {
  try {
    const res = await fetch('/api/screener/records?limit=15')
    const data: ApiResponse<Array<{ id: number; name: string; result_count: number; created_at: string }>> = await res.json()
    if (data.success) screenerRecords.value = data.data ?? []
  } catch { /* ignore */ }
}

/** 从条件选股记录设为今日推荐 */
async function applyFromScreener(recordId: number) {
  applyingFromScreener.value = true
  try {
    const res = await fetch('/api/daily/from_screener', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ record_id: recordId, date: dateFilter.value }),
    })
    const data = await res.json()
    if (data.success) {
      notify(data.message, 'success')
      await loadRecommendations()
      await loadStatus()
    } else {
      notify(data.message || '导入失败', 'error')
    }
  } finally {
    applyingFromScreener.value = false
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

function taskStatusLabel(s: string) {
  return { pending: '等待中', running: '运行中', completed: '已完成', failed: '失败', cancelled: '已停止' }[s] || s
}

function taskStatusCls(s: string) {
  if (s === 'running') return 'bg-blue-100 text-blue-700 border-blue-200'
  if (s === 'completed') return 'bg-green-100 text-green-700 border-green-200'
  if (s === 'failed') return 'bg-red-100 text-red-700 border-red-200'
  if (s === 'cancelled') return 'bg-amber-100 text-amber-700 border-amber-200'
  return 'bg-gray-100 text-gray-600 border-gray-200'
}

/** 运行中任务数（含 pending） */
const runningTaskCount = computed(() =>
  analysisQueue.value.filter(t => t.status === 'running' || t.status === 'pending').length
)

const stoppingTaskId = ref<string | null>(null)
async function stopTask(taskId: string) {
  stoppingTaskId.value = taskId
  try {
    const res = await fetch('/api/daily/stop_analysis', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: taskId }),
    })
    const data = await res.json()
    if (data.success) {
      notify('已发送停止信号', 'info')
      await loadAnalysisQueue()
    } else {
      notify(data.message || '停止失败', 'error')
    }
  } finally {
    stoppingTaskId.value = null
  }
}

onMounted(async () => {
  await Promise.all([loadStatus(), loadRecommendations(), loadAnalysisQueue(), loadScreenerRecords()])
  if (hasRunningTask.value) startQueuePolling()
})

onUnmounted(() => {
  stopQueuePolling()
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
          {{ analyzing ? '提交中…' : '立即分析' }}
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
        <div class="text-lg font-bold text-gray-700 truncate">{{ status?.last_update ?? '-' }}</div>
        <div class="text-xs text-gray-500 mt-1">最后更新</div>
        <button @click="loadStatus(); loadRecommendations()"
                class="mt-3 w-full text-xs px-3 py-1.5 border border-gray-300 rounded-lg hover:bg-gray-50 transition">
          刷新
        </button>
      </div>
    </div>

    <!-- 多线程分析任务队列（常显，展示各任务进度与停止） -->
    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div class="px-5 py-4 border-b border-gray-200">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <span class="inline-block w-2 h-2 rounded-full bg-indigo-500 animate-pulse" v-if="hasRunningTask"></span>
            分析任务队列
            <span v-if="analysisQueue.length" class="text-xs font-normal text-gray-500">
              共 {{ analysisQueue.length }} 个任务<span v-if="runningTaskCount">，{{ runningTaskCount }} 个运行中</span>
            </span>
          </h3>
          <button @click="loadAnalysisQueue" class="text-xs text-indigo-600 hover:text-indigo-700">刷新</button>
        </div>
        <p class="text-xs text-gray-400 mt-1">支持并行多任务，可多次点击「立即分析」；运行中任务可点击「停止」中止</p>
      </div>
      <div class="divide-y divide-gray-100 min-h-[80px]">
        <div v-if="!analysisQueue.length" class="px-5 py-8 text-center text-gray-400 text-sm">
          暂无分析任务，点击「立即分析」开始
        </div>
        <div v-for="t in analysisQueue" :key="t.id"
             class="px-5 py-4 flex flex-col gap-2">
          <div class="flex items-center justify-between gap-2">
            <span class="text-xs font-mono text-gray-500 truncate">{{ t.id }}</span>
            <div class="flex items-center gap-2 shrink-0">
              <span class="text-xs px-2 py-0.5 rounded border" :class="taskStatusCls(t.status)">
                {{ taskStatusLabel(t.status) }}
              </span>
              <button v-if="t.status === 'pending' || t.status === 'running'"
                      @click="stopTask(t.id)"
                      :disabled="stoppingTaskId === t.id"
                      class="text-xs px-2 py-0.5 rounded border border-amber-300 text-amber-700 hover:bg-amber-50 disabled:opacity-50">
                {{ stoppingTaskId === t.id ? '停止中…' : '停止' }}
              </button>
            </div>
          </div>
          <div v-if="t.status === 'running' && t.total > 0" class="space-y-1">
            <div class="flex justify-between text-xs text-gray-600">
              <span class="truncate mr-2">{{ t.message }}</span>
              <span class="shrink-0">{{ t.progress }} / {{ t.total }}</span>
            </div>
            <div class="h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div class="h-full bg-indigo-500 rounded-full transition-all duration-300"
                   :style="{ width: Math.min(100, (t.progress / t.total) * 100) + '%' }"></div>
            </div>
            <div v-if="t.current_stock" class="text-xs text-indigo-600 truncate">
              当前: {{ t.current_stock.name }} ({{ t.current_stock.symbol }})
            </div>
          </div>
          <div v-else class="text-xs text-gray-500">{{ t.message }}</div>
          <div v-if="t.status === 'completed' && t.result" class="text-xs text-green-600">
            推荐 {{ t.result.count }} 只 · {{ t.result.date }}
          </div>
          <div v-if="t.status === 'cancelled'" class="text-xs text-amber-600">已停止</div>
          <div v-if="t.status === 'failed' && t.error" class="text-xs text-red-600 truncate">{{ t.error }}</div>
        </div>
      </div>
    </div>

    <!-- 从条件选股导入 -->
    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <button @click="showScreenerImport = !showScreenerImport"
              class="w-full px-5 py-4 flex items-center justify-between text-left hover:bg-gray-50 transition">
        <h3 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
          <span>📋</span> 从条件选股导入
        </h3>
        <span class="text-xs text-gray-400">{{ showScreenerImport ? '收起' : '展开' }}</span>
      </button>
      <div v-show="showScreenerImport" class="border-t border-gray-100 px-5 py-4">
        <div class="flex items-center justify-between mb-3">
          <p class="text-xs text-gray-500">将条件选股结果设为当前选中日期的推荐</p>
          <button @click="loadScreenerRecords()" class="text-xs text-indigo-600 hover:text-indigo-700">刷新</button>
        </div>
        <div v-if="screenerRecords.length" class="space-y-2 max-h-48 overflow-y-auto">
          <div v-for="r in screenerRecords" :key="r.id"
               class="flex items-center justify-between gap-3 py-2 px-3 rounded-lg bg-gray-50 hover:bg-gray-100">
            <div class="min-w-0 flex-1">
              <div class="text-sm font-medium text-gray-800 truncate">{{ r.name }}</div>
              <div class="text-xs text-gray-500">{{ r.result_count }} 只 · {{ r.created_at }}</div>
            </div>
            <button @click="applyFromScreener(r.id)" :disabled="applyingFromScreener"
                    class="shrink-0 text-xs px-3 py-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">
              导入为推荐
            </button>
          </div>
        </div>
        <div v-else class="text-xs text-gray-400 py-4">暂无选股记录，请先在「条件选股」中运行筛选</div>
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
        {{ analyzing ? '提交中…' : '开始分析' }}
      </button>
    </div>
  </div>
</template>
