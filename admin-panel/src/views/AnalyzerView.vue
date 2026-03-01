<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { fetchAnalysisRules, analyzeStock, fetchAnalysisHistory } from '../api'
import type { AnalysisRule, AnalysisReport, RuleResult, AnalysisRunRecord } from '../types'
import ToastNotify from '../components/ToastNotify.vue'
import AddToWatchlist from '../components/AddToWatchlist.vue'

const route = useRoute()

const rules = ref<AnalysisRule[]>([])
const selectedRules = ref<string[]>([])
const stockCode = ref('')
const loading = ref(false)
const report = ref<AnalysisReport | null>(null)
const history = ref<AnalysisReport[]>([])
const analysisRunHistory = ref<AnalysisRunRecord[]>([])
const toast = ref({ show: false, msg: '', type: 'info' })

function notify(msg: string, type = 'info') {
  toast.value = { show: true, msg, type }
  setTimeout(() => (toast.value.show = false), 3000)
}

const coreRules = computed(() => rules.value.filter(r => r.weight > 0))
const sectorRules = computed(() => rules.value.filter(r => r.weight === 0))

const sortedRuleResults = computed<[string, RuleResult][]>(() => {
  if (!report.value) return []
  return Object.entries(report.value.rule_results)
    .sort((a, b) => b[1].weight - a[1].weight)
})

function scoreColor(s: number): string {
  if (s >= 75) return 'text-green-600'
  if (s >= 55) return 'text-blue-600'
  if (s >= 40) return 'text-amber-600'
  return 'text-red-600'
}
function scoreBg(s: number): string {
  if (s >= 75) return 'bg-green-500'
  if (s >= 55) return 'bg-blue-500'
  if (s >= 40) return 'bg-amber-500'
  return 'bg-red-500'
}
function recBadge(rec: string): string {
  if (rec.includes('强烈推荐') || rec.includes('推荐买入')) return 'bg-green-100 text-green-800 border-green-200'
  if (rec.includes('建议买入') || rec.includes('谨慎买入')) return 'bg-blue-100 text-blue-800 border-blue-200'
  if (rec.includes('持有') || rec.includes('观望')) return 'bg-amber-100 text-amber-800 border-amber-200'
  return 'bg-red-100 text-red-800 border-red-200'
}

async function loadRules() {
  const res = await fetchAnalysisRules()
  if (res.success) {
    rules.value = res.data
    selectedRules.value = res.data.filter(r => r.weight > 0).map(r => r.rule_id)
  }
}

async function loadAnalysisRunHistory() {
  const res = await fetchAnalysisHistory(30)
  if (res.success) analysisRunHistory.value = res.data
}

function runStatusLabel(status: string): string {
  return { pending: '等待中', running: '运行中', completed: '已完成', failed: '失败', cancelled: '已停止' }[status] || status
}

function runStatusCls(status: string): string {
  if (status === 'completed') return 'bg-green-100 text-green-800'
  if (status === 'failed') return 'bg-red-100 text-red-800'
  if (status === 'running') return 'bg-indigo-100 text-indigo-800'
  if (status === 'cancelled') return 'bg-amber-100 text-amber-800'
  return 'bg-gray-100 text-gray-600'
}

function formatRunTime(iso: string): string {
  if (!iso) return '-'
  try {
    const d = new Date(iso)
    return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return iso
  }
}

async function doAnalyze() {
  const code = stockCode.value.trim()
  if (!code) { notify('请输入股票代码', 'error'); return }
  loading.value = true
  report.value = null
  try {
    const res = await analyzeStock({
      stock_code: code,
      rule_ids: selectedRules.value.length ? selectedRules.value : undefined,
    })
    if (res.success) {
      report.value = res.data
      if (!res.data.error) {
        history.value.unshift(res.data)
        if (history.value.length > 20) history.value.pop()
      }
      notify(res.data.error ? `分析异常: ${res.data.error}` : `分析完成: ${res.data.stock_name} 综合${res.data.comprehensive_score}分`, res.data.error ? 'error' : 'success')
    } else {
      notify(res.message ?? '分析失败', 'error')
    }
  } finally {
    loading.value = false
  }
}

function loadFromHistory(h: AnalysisReport) {
  report.value = h
  stockCode.value = h.stock_code
}

function toggleRule(id: string) {
  const idx = selectedRules.value.indexOf(id)
  if (idx >= 0) selectedRules.value.splice(idx, 1)
  else selectedRules.value.push(id)
}

onMounted(async () => {
  await loadRules()
  await loadAnalysisRunHistory()
  const code = route.query.code as string | undefined
  if (code) {
    stockCode.value = code
    doAnalyze()
  }
})
</script>

<template>
  <ToastNotify :show="toast.show" :message="toast.msg" :type="toast.type" />

  <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">

    <!-- 左侧主面板 -->
    <div class="lg:col-span-3 space-y-5">

      <!-- 输入区 -->
      <div class="bg-white rounded-xl border border-gray-200 p-5">
        <div class="flex flex-col sm:flex-row gap-3">
          <div class="flex-1">
            <label class="block text-xs font-medium text-gray-500 mb-1">股票代码</label>
            <input v-model="stockCode" @keyup.enter="doAnalyze" :disabled="loading"
                   class="w-full text-lg font-mono border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                   placeholder="输入代码，如 000001 / 00700 / AAPL" />
          </div>
          <div class="flex items-end">
            <button @click="doAnalyze" :disabled="loading || !stockCode.trim()"
                    class="px-6 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition whitespace-nowrap">
              {{ loading ? '分析中…' : '开始分析' }}
            </button>
          </div>
        </div>
        <p class="text-xs text-gray-400 mt-2">支持 A股(6位数字) / 港股(5位数字) / 美股(字母代码)，自动识别市场</p>
      </div>

      <!-- 规则选择 -->
      <div class="bg-white rounded-xl border border-gray-200 p-5">
        <h3 class="text-sm font-semibold text-gray-700 mb-3">分析规则配置</h3>
        <div class="space-y-3">
          <div>
            <div class="text-xs text-gray-500 mb-2">核心规则</div>
            <div class="flex flex-wrap gap-2">
              <button v-for="r in coreRules" :key="r.rule_id" @click="toggleRule(r.rule_id)"
                      class="text-xs px-3 py-1.5 rounded-lg border transition"
                      :class="selectedRules.includes(r.rule_id)
                        ? 'bg-indigo-600 text-white border-indigo-600'
                        : 'bg-white text-gray-600 border-gray-300 hover:border-indigo-400'">
                {{ r.name }} <span class="opacity-60">({{ (r.weight * 100).toFixed(0) }}%)</span>
              </button>
            </div>
          </div>
          <div v-if="sectorRules.length">
            <div class="text-xs text-gray-500 mb-2">行业板块规则 <span class="text-gray-400">（可选叠加）</span></div>
            <div class="flex flex-wrap gap-2">
              <button v-for="r in sectorRules" :key="r.rule_id" @click="toggleRule(r.rule_id)"
                      class="text-xs px-3 py-1.5 rounded-lg border transition"
                      :class="selectedRules.includes(r.rule_id)
                        ? 'bg-purple-600 text-white border-purple-600'
                        : 'bg-white text-gray-600 border-gray-300 hover:border-purple-400'">
                {{ r.name }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 分析结果 -->
      <div v-if="report && !report.error" class="space-y-5">

        <!-- 头部卡片 -->
        <div class="bg-white rounded-xl border border-gray-200 p-6">
          <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div class="flex items-center gap-3">
                <h2 class="text-2xl font-bold text-gray-900">{{ report.stock_name }}</h2>
                <span class="text-sm font-mono text-gray-500">{{ report.stock_code }}</span>
                <span class="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">{{ report.market_label }}</span>
              </div>
              <p class="text-xs text-gray-400 mt-1">{{ report.analysis_date }} · {{ report.currency }}</p>
            </div>
            <div class="flex items-center gap-6">
              <div class="text-center">
                <div class="text-3xl font-bold" :class="report.price_info.price_change >= 0 ? 'text-red-600' : 'text-green-600'">
                  {{ report.price_info.current_price.toFixed(2) }}
                </div>
                <div class="text-xs" :class="report.price_info.price_change >= 0 ? 'text-red-500' : 'text-green-500'">
                  {{ report.price_info.price_change >= 0 ? '+' : '' }}{{ report.price_info.price_change.toFixed(2) }}%
                </div>
              </div>
              <div class="text-center">
                <div class="text-3xl font-bold" :class="scoreColor(report.comprehensive_score)">
                  {{ report.comprehensive_score }}
                </div>
                <div class="text-xs text-gray-500">综合评分</div>
              </div>
            </div>
          </div>
          <div class="mt-4">
            <span class="inline-block text-sm font-medium px-4 py-1.5 rounded-full border" :class="recBadge(report.recommendation)">
              {{ report.recommendation }}
            </span>
            <AddToWatchlist :symbol="report.stock_code" :stock-name="report.stock_name" :market="report.market_label" />
          </div>
        </div>

        <!-- 评分仪表盘 -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div v-for="[rid, rr] in sortedRuleResults" :key="rid"
               class="bg-white rounded-xl border border-gray-200 p-4">
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-semibold text-gray-700">{{ rr.name }}</span>
              <span class="text-lg font-bold" :class="scoreColor(rr.score)">{{ rr.score }}</span>
            </div>
            <div class="w-full bg-gray-100 rounded-full h-2 mb-2">
              <div class="h-2 rounded-full transition-all" :class="scoreBg(rr.score)"
                   :style="{ width: rr.score + '%' }"></div>
            </div>
            <p class="text-xs text-gray-500 leading-relaxed">{{ rr.details }}</p>
            <div v-if="rr.weight > 0" class="text-[10px] text-gray-400 mt-1">权重 {{ (rr.weight * 100).toFixed(0) }}%</div>
          </div>
        </div>

        <!-- 技术指标明细 -->
        <div class="bg-white rounded-xl border border-gray-200 p-5">
          <h3 class="text-sm font-semibold text-gray-700 mb-3">技术指标明细</h3>
          <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div class="text-center p-3 bg-gray-50 rounded-lg">
              <div class="text-xs text-gray-500 mb-1">均线趋势</div>
              <div class="text-sm font-semibold"
                   :class="report.technical.ma_trend === '多头排列' ? 'text-green-600' : report.technical.ma_trend === '空头排列' ? 'text-red-600' : 'text-gray-700'">
                {{ report.technical.ma_trend || '-' }}
              </div>
            </div>
            <div class="text-center p-3 bg-gray-50 rounded-lg">
              <div class="text-xs text-gray-500 mb-1">RSI</div>
              <div class="text-sm font-semibold" :class="(report.technical.rsi as number) > 70 ? 'text-red-600' : (report.technical.rsi as number) < 30 ? 'text-green-600' : 'text-gray-700'">
                {{ typeof report.technical.rsi === 'number' ? (report.technical.rsi as number).toFixed(1) : '-' }}
              </div>
            </div>
            <div class="text-center p-3 bg-gray-50 rounded-lg">
              <div class="text-xs text-gray-500 mb-1">MACD</div>
              <div class="text-sm font-semibold"
                   :class="report.technical.macd_signal === '金叉向上' ? 'text-green-600' : report.technical.macd_signal === '死叉向下' ? 'text-red-600' : 'text-gray-700'">
                {{ report.technical.macd_signal || '-' }}
              </div>
            </div>
            <div class="text-center p-3 bg-gray-50 rounded-lg">
              <div class="text-xs text-gray-500 mb-1">布林带位置</div>
              <div class="text-sm font-semibold text-gray-700">
                {{ typeof report.technical.bb_position === 'number' ? (report.technical.bb_position as number).toFixed(2) : '-' }}
              </div>
            </div>
            <div class="text-center p-3 bg-gray-50 rounded-lg">
              <div class="text-xs text-gray-500 mb-1">成交量</div>
              <div class="text-sm font-semibold"
                   :class="String(report.technical.volume_status).includes('上涨') ? 'text-green-600' : String(report.technical.volume_status).includes('下跌') ? 'text-red-600' : 'text-gray-700'">
                {{ report.technical.volume_status || '-' }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="report && report.error" class="bg-white rounded-xl border border-red-200 p-8 text-center">
        <div class="text-red-400 text-4xl mb-3">!</div>
        <p class="text-red-600 font-medium">{{ report.error }}</p>
        <p class="text-gray-500 text-sm mt-1">请检查股票代码是否正确或稍后重试</p>
      </div>

      <!-- 空状态 -->
      <div v-else-if="!loading" class="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-400">
        <svg class="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" stroke-width="1" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
        </svg>
        <p class="text-sm">输入股票代码开始分析</p>
        <p class="text-xs mt-1">支持 A股 / 港股 / 美股，自动识别市场类型</p>
      </div>
    </div>

    <!-- 右侧：分析运行历史 + 本页历史 -->
    <div class="space-y-4">
      <!-- 分析运行历史（批量分析日志） -->
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden sticky top-4">
        <div class="p-4 border-b border-gray-200 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-gray-700">分析运行历史</h3>
          <button @click="loadAnalysisRunHistory" class="text-xs text-indigo-600 hover:text-indigo-700">刷新</button>
        </div>
        <div class="divide-y max-h-[40vh] overflow-y-auto">
          <div v-if="!analysisRunHistory.length" class="p-6 text-center text-gray-400 text-xs">暂无运行记录，请在「每日推荐」中执行立即分析</div>
          <div v-for="r in analysisRunHistory" :key="r.id" class="p-3 text-left">
            <div class="flex items-center justify-between gap-2 mb-1">
              <span class="text-xs font-mono text-gray-500 truncate">{{ r.task_id }}</span>
              <span class="text-xs px-1.5 py-0.5 rounded shrink-0" :class="runStatusCls(r.status)">{{ runStatusLabel(r.status) }}</span>
            </div>
            <div class="text-[11px] text-gray-500">
              <div>开始 {{ formatRunTime(r.started_at) }}</div>
              <div v-if="r.finished_at">结束 {{ formatRunTime(r.finished_at) }}</div>
              <div v-if="r.status === 'completed' && r.result_count != null" class="text-green-600 mt-0.5">
                推荐 {{ r.result_count }} 只 · {{ r.result_date || '-' }}
              </div>
              <div v-if="r.status === 'failed' && r.error_message" class="text-red-600 mt-0.5 truncate" :title="r.error_message">{{ r.error_message }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 本页分析历史（单只股票） -->
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div class="p-4 border-b border-gray-200">
          <h3 class="text-sm font-semibold text-gray-700">本页历史</h3>
        </div>
        <div class="divide-y max-h-[35vh] overflow-y-auto">
          <div v-if="!history.length" class="p-8 text-center text-gray-400 text-sm">暂无分析记录</div>
          <div v-for="(h, i) in history" :key="i"
               class="p-3 hover:bg-gray-50 cursor-pointer transition"
               @click="loadFromHistory(h)">
            <div class="flex items-center justify-between">
              <div>
                <div class="text-sm font-medium">{{ h.stock_name }}</div>
                <div class="text-xs text-gray-500 font-mono">{{ h.stock_code }} · {{ h.market_label }}</div>
              </div>
              <div class="text-right">
                <div class="text-sm font-bold" :class="scoreColor(h.comprehensive_score)">{{ h.comprehensive_score }}</div>
                <div class="text-[10px]" :class="h.price_info.price_change >= 0 ? 'text-red-500' : 'text-green-500'">
                  {{ h.price_info.price_change >= 0 ? '+' : '' }}{{ h.price_info.price_change.toFixed(2) }}%
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
