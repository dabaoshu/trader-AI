<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { fetchPresets, runScreener, fetchRecords, fetchRecordDetail, deleteRecord as apiDelete } from '../api'
import type { PresetTemplate, ScreenerConditions, CustomRule, StockItem, ScreenerRecord, FieldOption, OpOption } from '../types'
import ToastNotify from '../components/ToastNotify.vue'
import AddToWatchlist from '../components/AddToWatchlist.vue'

const FIELD_OPTIONS: FieldOption[] = [
  { value: 'current_price', label: '当前价格' },
  { value: 'total_score', label: '综合评分' },
  { value: 'tech_score', label: '技术评分' },
  { value: 'auction_score', label: '竞价评分' },
  { value: 'auction_ratio', label: '竞价涨幅(%)' },
  { value: 'rsi', label: 'RSI' },
  { value: 'market_cap_billion', label: '市值(亿)' },
  { value: 'entry_price', label: '入场价' },
  { value: 'stop_loss', label: '止损价' },
  { value: 'target_price', label: '目标价' },
  { value: 'symbol', label: '股票代码' },
  { value: 'stock_name', label: '股票名称' },
  { value: 'market', label: '市场' },
  { value: 'strategy', label: '策略' },
]

const OP_OPTIONS: OpOption[] = [
  { value: 'gt', label: '>' },
  { value: 'gte', label: '≥' },
  { value: 'lt', label: '<' },
  { value: 'lte', label: '≤' },
  { value: 'eq', label: '=' },
  { value: 'neq', label: '≠' },
  { value: 'contains', label: '包含' },
]

const GAP_OPTIONS = [
  { value: 'gap_up', label: '高开 ↑' },
  { value: 'flat', label: '平开 →' },
  { value: 'gap_down', label: '低开 ↓' },
]
const CONFIDENCE_OPTIONS = [
  { value: 'very_high', label: '非常高' },
  { value: 'high', label: '高' },
  { value: 'medium', label: '中等' },
]
const MARKET_OPTIONS = ['上海主板', '深圳主板', '中小板', '创业板']

const presets = ref<PresetTemplate[]>([])
const records = ref<ScreenerRecord[]>([])
const loading = ref(false)
const activePreset = ref('')
const toast = ref({ show: false, msg: '', type: 'info' })

const form = reactive({
  recordName: '',
  priceMin: '' as string | number,
  priceMax: '' as string | number,
  totalScoreMin: '' as string | number,
  techScoreMin: '' as string | number,
  auctionRatioMin: '' as string | number,
  auctionRatioMax: '' as string | number,
  rsiMin: '' as string | number,
  rsiMax: '' as string | number,
  marketCapMin: '' as string | number,
  marketCapMax: '' as string | number,
  keyword: '',
  gapTypes: [] as string[],
  confidenceLevels: [] as string[],
  markets: [] as string[],
})

const customRules = ref<{ field: string; op: CustomRule['op']; value: string }[]>([])

const resultStocks = ref<StockItem[]>([])
const resultRecordId = ref<number | null>(null)
const showResult = ref(false)

function notify(msg: string, type = 'info') {
  toast.value = { show: true, msg, type }
  setTimeout(() => (toast.value.show = false), 3000)
}

function resetForm() {
  form.recordName = ''
  form.priceMin = ''
  form.priceMax = ''
  form.totalScoreMin = ''
  form.techScoreMin = ''
  form.auctionRatioMin = ''
  form.auctionRatioMax = ''
  form.rsiMin = ''
  form.rsiMax = ''
  form.marketCapMin = ''
  form.marketCapMax = ''
  form.keyword = ''
  form.gapTypes = []
  form.confidenceLevels = []
  form.markets = []
  customRules.value = []
  activePreset.value = ''
}

function applyPreset(p: PresetTemplate) {
  resetForm()
  activePreset.value = p.key
  form.recordName = p.name
  const c = p.conditions
  if (c.price_min != null) form.priceMin = c.price_min
  if (c.price_max != null) form.priceMax = c.price_max
  if (c.total_score_min != null) form.totalScoreMin = c.total_score_min
  if (c.tech_score_min != null) form.techScoreMin = c.tech_score_min
  if (c.auction_ratio_min != null) form.auctionRatioMin = c.auction_ratio_min
  if (c.auction_ratio_max != null) form.auctionRatioMax = c.auction_ratio_max
  if (c.rsi_min != null) form.rsiMin = c.rsi_min
  if (c.rsi_max != null) form.rsiMax = c.rsi_max
  if (c.market_cap_min != null) form.marketCapMin = c.market_cap_min
  if (c.market_cap_max != null) form.marketCapMax = c.market_cap_max
  if (c.gap_types) form.gapTypes = [...c.gap_types]
  if (c.confidence_levels) form.confidenceLevels = [...c.confidence_levels]
  if (c.markets) form.markets = [...c.markets]
  notify(`已加载模板「${p.name}」`, 'info')
}

function gatherConditions(): ScreenerConditions {
  const cond: ScreenerConditions = {}
  const num = (v: string | number) => (v === '' ? undefined : Number(v))
  if (num(form.priceMin) != null) cond.price_min = num(form.priceMin)
  if (num(form.priceMax) != null) cond.price_max = num(form.priceMax)
  if (num(form.totalScoreMin) != null) cond.total_score_min = num(form.totalScoreMin)
  if (num(form.techScoreMin) != null) cond.tech_score_min = num(form.techScoreMin)
  if (num(form.auctionRatioMin) != null) cond.auction_ratio_min = num(form.auctionRatioMin)
  if (num(form.auctionRatioMax) != null) cond.auction_ratio_max = num(form.auctionRatioMax)
  if (num(form.rsiMin) != null) cond.rsi_min = num(form.rsiMin)
  if (num(form.rsiMax) != null) cond.rsi_max = num(form.rsiMax)
  if (num(form.marketCapMin) != null) cond.market_cap_min = num(form.marketCapMin)
  if (num(form.marketCapMax) != null) cond.market_cap_max = num(form.marketCapMax)
  if (form.gapTypes.length) cond.gap_types = form.gapTypes
  if (form.confidenceLevels.length) cond.confidence_levels = form.confidenceLevels
  if (form.markets.length) cond.markets = form.markets
  if (form.keyword) cond.keyword = form.keyword
  const rules: CustomRule[] = customRules.value
    .filter(r => r.field && r.op && r.value !== '')
    .map(r => ({ field: r.field, op: r.op, value: isNaN(Number(r.value)) ? r.value : Number(r.value) }))
  if (rules.length) cond.custom_rules = rules
  return cond
}

async function doScreen() {
  loading.value = true
  try {
    const conditions = gatherConditions()
    const res = await runScreener({
      name: form.recordName || undefined,
      conditions,
      preset_key: activePreset.value || undefined,
    })
    if (res.success) {
      notify(res.message ?? '选股完成', 'success')
      resultStocks.value = res.data.stocks
      resultRecordId.value = res.data.record_id
      showResult.value = true
      await loadHistory()
    } else {
      notify(res.message ?? '选股失败', 'error')
    }
  } finally {
    loading.value = false
  }
}

function addRule() {
  customRules.value.push({ field: 'current_price', op: 'gte', value: '' })
}
function removeRule(idx: number) {
  customRules.value.splice(idx, 1)
}

async function loadHistory() {
  const res = await fetchRecords(20)
  if (res.success) records.value = res.data
}

async function loadRecord(id: number) {
  const res = await fetchRecordDetail(id)
  if (res.success) {
    const rec = res.data
    resultStocks.value = rec.result_data?.length ? rec.result_data : rec.result_summary?.top_stocks ?? []
    resultRecordId.value = rec.id
    showResult.value = true
    notify(`已加载记录「${rec.name}」(${rec.result_count} 只)`, 'info')
  }
}

async function removeRecord(id: number) {
  if (!confirm('确定删除？')) return
  const res = await apiDelete(id)
  if (res.success) { notify('已删除', 'success'); await loadHistory() }
}

function confidenceTag(c: string): string {
  return ({ very_high: '非常高', high: '高', medium: '中等' } as Record<string, string>)[c] || c
}
function confidenceCls(c: string): string {
  if (c === 'very_high') return 'bg-green-100 text-green-800'
  if (c === 'high') return 'bg-blue-100 text-blue-800'
  return 'bg-gray-100 text-gray-700'
}

onMounted(async () => {
  const pRes = await fetchPresets()
  if (pRes.success) presets.value = pRes.data
  await loadHistory()
})
</script>

<template>
  <ToastNotify :show="toast.show" :message="toast.msg" :type="toast.type" />

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <!-- 左侧：条件面板 -->
    <div class="lg:col-span-2 space-y-5">

      <!-- 快捷模板 -->
      <div class="bg-white rounded-xl border border-gray-200 p-5">
        <h2 class="text-sm font-semibold text-gray-700 mb-3">快捷选股模板</h2>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <button v-for="p in presets" :key="p.key" @click="applyPreset(p)"
                  class="text-left p-3 rounded-xl border-2 transition-all hover:border-indigo-400"
                  :class="activePreset === p.key ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200'">
            <div class="text-sm font-semibold mb-1">{{ p.name }}</div>
            <p class="text-xs text-gray-500 leading-relaxed">{{ p.description }}</p>
          </button>
        </div>
      </div>

      <!-- 自定义条件 -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold text-gray-700">自定义筛选条件</h2>
          <button @click="resetForm" class="text-xs text-gray-500 hover:text-gray-700">重置</button>
        </div>

        <!-- 记录名称 -->
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">记录名称</label>
          <input v-model="form.recordName" class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="给本次选股起个名字（可选）" />
        </div>

        <!-- 价格 -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">最低价格 (元)</label>
            <input v-model="form.priceMin" type="number" step="0.1" class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="不限" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">最高价格 (元)</label>
            <input v-model="form.priceMax" type="number" step="0.1" class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="不限" />
          </div>
        </div>

        <!-- 评分 -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">综合评分 ≥</label>
            <input v-model="form.totalScoreMin" type="number" step="0.01" min="0" max="1" class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="0.00" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">技术评分 ≥</label>
            <input v-model="form.techScoreMin" type="number" step="0.01" min="0" max="1" class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="0.00" />
          </div>
        </div>

        <!-- 竞价 -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">竞价涨幅 ≥ (%)</label>
            <input v-model="form.auctionRatioMin" type="number" step="0.1" class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="不限" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">竞价涨幅 ≤ (%)</label>
            <input v-model="form.auctionRatioMax" type="number" step="0.1" class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="不限" />
          </div>
        </div>

        <!-- RSI -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">RSI ≥</label>
            <input v-model="form.rsiMin" type="number" step="1" min="0" max="100" class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="不限" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">RSI ≤</label>
            <input v-model="form.rsiMax" type="number" step="1" min="0" max="100" class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="不限" />
          </div>
        </div>

        <!-- 市值 -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">市值 ≥ (亿)</label>
            <input v-model="form.marketCapMin" type="number" step="1" class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="不限" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">市值 ≤ (亿)</label>
            <input v-model="form.marketCapMax" type="number" step="1" class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="不限" />
          </div>
        </div>

        <!-- 跳空类型 -->
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-2">跳空类型</label>
          <div class="flex flex-wrap gap-3">
            <label v-for="g in GAP_OPTIONS" :key="g.value" class="inline-flex items-center gap-1.5 text-sm cursor-pointer">
              <input type="checkbox" :value="g.value" v-model="form.gapTypes" class="rounded" /> {{ g.label }}
            </label>
          </div>
        </div>

        <!-- 信心等级 -->
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-2">信心等级</label>
          <div class="flex flex-wrap gap-3">
            <label v-for="c in CONFIDENCE_OPTIONS" :key="c.value" class="inline-flex items-center gap-1.5 text-sm cursor-pointer">
              <input type="checkbox" :value="c.value" v-model="form.confidenceLevels" class="rounded" /> {{ c.label }}
            </label>
          </div>
        </div>

        <!-- 市场板块 -->
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-2">市场板块</label>
          <div class="flex flex-wrap gap-3">
            <label v-for="m in MARKET_OPTIONS" :key="m" class="inline-flex items-center gap-1.5 text-sm cursor-pointer">
              <input type="checkbox" :value="m" v-model="form.markets" class="rounded" /> {{ m }}
            </label>
          </div>
        </div>

        <!-- 关键词 -->
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">关键词搜索</label>
          <input v-model="form.keyword" class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="股票代码或名称" />
        </div>

        <!-- 手动自定义条件 -->
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-2">手动自定义条件 <span class="text-gray-400">（所有条件同时满足）</span></label>
          <div class="space-y-2">
            <div v-for="(rule, idx) in customRules" :key="idx" class="flex items-center gap-2">
              <select v-model="rule.field" class="text-sm border border-gray-300 rounded-lg px-2 py-1.5 w-32 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                <option v-for="f in FIELD_OPTIONS" :key="f.value" :value="f.value">{{ f.label }}</option>
              </select>
              <select v-model="rule.op" class="text-sm border border-gray-300 rounded-lg px-2 py-1.5 w-20 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                <option v-for="o in OP_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
              </select>
              <input v-model="rule.value" class="flex-1 text-sm border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="值" />
              <button @click="removeRule(idx)" class="text-gray-400 hover:text-red-500 p-1">✕</button>
            </div>
          </div>
          <button @click="addRule" class="mt-2 text-xs px-3 py-1.5 border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-600">
            + 添加条件
          </button>
        </div>

        <!-- 执行 -->
        <button @click="doScreen" :disabled="loading"
                class="w-full py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition">
          {{ loading ? '筛选中…' : '开始选股' }}
        </button>
      </div>

      <!-- 筛选结果 -->
      <div v-if="showResult" class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div class="p-4 border-b border-gray-200 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-gray-700">
            筛选结果
            <span class="ml-2 px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded-full text-xs font-bold">{{ resultStocks.length }}</span>
          </h3>
          <span v-if="resultRecordId" class="text-xs text-gray-400">#{{ resultRecordId }}</span>
        </div>

        <div v-if="resultStocks.length" class="p-4 border-b bg-gray-50">
          <div class="grid grid-cols-2 md:grid-cols-5 gap-4 text-center text-xs">
            <div><div class="text-lg font-bold text-indigo-600">{{ resultStocks.length }}</div><div class="text-gray-500">筛选结果</div></div>
            <div><div class="text-lg font-bold text-green-600">{{ resultStocks.filter(s => s.confidence === 'very_high').length }}</div><div class="text-gray-500">强烈推荐</div></div>
            <div><div class="text-lg font-bold text-purple-600">{{ (resultStocks.reduce((s, x) => s + (x.total_score || 0), 0) / resultStocks.length).toFixed(3) }}</div><div class="text-gray-500">平均评分</div></div>
            <div><div class="text-lg font-bold text-orange-600">{{ [...new Set(resultStocks.map(s => s.market))].length }}</div><div class="text-gray-500">覆盖市场</div></div>
            <div><div class="text-lg font-bold text-cyan-600">¥{{ Math.min(...resultStocks.map(s => s.current_price || 0)).toFixed(0) }}-{{ Math.max(...resultStocks.map(s => s.current_price || 0)).toFixed(0) }}</div><div class="text-gray-500">价格区间</div></div>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 border-b text-left">
              <tr>
                <th class="p-3 font-semibold text-gray-600">代码</th>
                <th class="p-3 font-semibold text-gray-600">名称</th>
                <th class="p-3 font-semibold text-gray-600">市场</th>
                <th class="p-3 font-semibold text-gray-600">价格</th>
                <th class="p-3 font-semibold text-gray-600">综合评分</th>
                <th class="p-3 font-semibold text-gray-600">竞价涨幅</th>
                <th class="p-3 font-semibold text-gray-600">信心</th>
                <th class="p-3 font-semibold text-gray-600">策略</th>
                <th class="p-3 font-semibold text-gray-600">自选</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="s in resultStocks" :key="s.symbol" class="hover:bg-gray-50">
                <td class="p-3 font-mono text-xs">{{ s.symbol }}</td>
                <td class="p-3 font-medium">{{ s.stock_name }}</td>
                <td class="p-3"><span class="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded">{{ s.market }}</span></td>
                <td class="p-3 font-semibold">¥{{ (s.current_price ?? 0).toFixed(2) }}</td>
                <td class="p-3"><span class="text-xs bg-indigo-600 text-white px-2 py-0.5 rounded-full">{{ (s.total_score ?? 0).toFixed(3) }}</span></td>
                <td class="p-3" :class="(s.auction_ratio ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'">{{ (s.auction_ratio ?? 0) >= 0 ? '+' : '' }}{{ (s.auction_ratio ?? 0).toFixed(1) }}%</td>
                <td class="p-3"><span class="text-xs px-2 py-0.5 rounded" :class="confidenceCls(s.confidence)">{{ confidenceTag(s.confidence) }}</span></td>
                <td class="p-3 max-w-xs"><p class="text-xs text-gray-600 truncate">{{ s.strategy }}</p></td>
                <td class="p-3"><AddToWatchlist :symbol="s.symbol" :stock-name="s.stock_name" :market="s.market" /></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!resultStocks.length" class="text-center py-10 text-gray-400 text-sm">没有符合条件的股票</div>
      </div>
    </div>

    <!-- 右侧：历史记录 -->
    <div>
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden sticky top-4">
        <div class="p-4 border-b border-gray-200">
          <h3 class="text-sm font-semibold text-gray-700">选股历史</h3>
        </div>
        <div class="divide-y max-h-[75vh] overflow-y-auto">
          <div v-if="!records.length" class="p-8 text-center text-gray-400 text-sm">暂无选股记录</div>
          <div v-for="rec in records" :key="rec.id"
               class="p-3 hover:bg-gray-50 transition cursor-pointer group"
               @click="loadRecord(rec.id)">
            <div class="flex items-start justify-between">
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium truncate">{{ rec.name }}</div>
                <div class="text-xs text-gray-500 mt-0.5">{{ rec.created_at }}</div>
                <div class="flex items-center gap-1 mt-1">
                  <span class="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">{{ rec.result_count }} 只</span>
                  <span v-if="rec.preset_key" class="text-xs bg-indigo-100 text-indigo-600 px-1.5 py-0.5 rounded">{{ rec.preset_key }}</span>
                </div>
              </div>
              <button class="text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity p-1"
                      @click.stop="removeRecord(rec.id)">✕</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
