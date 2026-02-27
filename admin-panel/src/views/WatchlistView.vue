<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import {
  fetchWatchlistGroups, addWatchlistGroup, renameWatchlistGroup,
  deleteWatchlistGroup, fetchWatchlistStocks, removeWatchlistStock,
  fetchRealtimeQuotes,
} from '../api'
import type { WatchlistGroup, WatchlistStock, RealtimeQuote } from '../types'
import ToastNotify from '../components/ToastNotify.vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const groups = ref<WatchlistGroup[]>([])
const activeGroupId = ref<number | null>(null)
const stocks = ref<WatchlistStock[]>([])
const quotes = ref<Record<string, RealtimeQuote>>({})
const loading = ref(false)
const quotesLoading = ref(false)
const toast = ref({ show: false, msg: '', type: 'info' })
const lastQuoteTime = ref('')

const editingGroupId = ref<number | null>(null)
const editingName = ref('')

let pollTimer: ReturnType<typeof setInterval> | null = null

function notify(msg: string, type = 'info') {
  toast.value = { show: true, msg, type }
  setTimeout(() => (toast.value.show = false), 3000)
}

const activeGroup = computed(() => groups.value.find(g => g.id === activeGroupId.value))

const enrichedStocks = computed(() =>
  stocks.value.map(s => ({
    ...s,
    quote: quotes.value[s.symbol] ?? null,
  }))
)

async function loadGroups() {
  const res = await fetchWatchlistGroups()
  if (res.success) {
    groups.value = res.data
    if (!activeGroupId.value && res.data.length) activeGroupId.value = res.data[0].id
  }
}

async function loadStocks() {
  if (!activeGroupId.value) { stocks.value = []; return }
  loading.value = true
  try {
    const res = await fetchWatchlistStocks(activeGroupId.value)
    if (res.success) stocks.value = res.data
  } finally {
    loading.value = false
  }
}

async function loadQuotes() {
  const symbols = stocks.value.map(s => s.symbol)
  if (!symbols.length) return
  quotesLoading.value = true
  try {
    const res = await fetchRealtimeQuotes(symbols)
    if (res.success) {
      quotes.value = res.data
      const first = Object.values(res.data)[0]
      if (first?.updated_at) lastQuoteTime.value = first.updated_at
    }
  } finally {
    quotesLoading.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(loadQuotes, 5000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

watch(activeGroupId, async () => {
  await loadStocks()
  await loadQuotes()
  startPolling()
})

async function createGroup() {
  const res = await addWatchlistGroup('新分组')
  if (res.success) {
    await loadGroups()
    activeGroupId.value = res.data.id
    startRename(res.data.id, res.data.name)
    notify('已创建新分组', 'success')
  }
}

function startRename(id: number, name: string) {
  editingGroupId.value = id
  editingName.value = name
  nextTick(() => {
    const el = document.getElementById(`rename-input-${id}`)
    if (el) (el as HTMLInputElement).focus()
  })
}

async function confirmRename() {
  if (!editingGroupId.value || !editingName.value.trim()) { editingGroupId.value = null; return }
  await renameWatchlistGroup(editingGroupId.value, editingName.value.trim())
  editingGroupId.value = null
  await loadGroups()
}

async function doDeleteGroup(id: number) {
  const g = groups.value.find(g => g.id === id)
  if (!confirm(`确定删除分组「${g?.name}」及其所有股票？`)) return
  await deleteWatchlistGroup(id)
  if (activeGroupId.value === id) activeGroupId.value = null
  await loadGroups()
  notify('分组已删除', 'success')
}

async function doRemoveStock(sid: number) {
  await removeWatchlistStock(sid)
  await loadStocks()
  await loadGroups()
}

function goAnalyze(code: string) {
  router.push({ path: '/analyzer', query: { code } })
}

function marketCls(m: string) {
  if (m === '上海主板') return 'bg-red-100 text-red-700'
  if (m === '深圳主板') return 'bg-blue-100 text-blue-700'
  if (m === '创业板') return 'bg-purple-100 text-purple-700'
  if (m === '中小板') return 'bg-amber-100 text-amber-700'
  return 'bg-gray-100 text-gray-600'
}

function fmtCap(v: number): string {
  if (!v) return '-'
  if (v >= 1e12) return (v / 1e12).toFixed(2) + '万亿'
  if (v >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toFixed(0)
}

function fmtVol(v: number): string {
  if (!v) return '-'
  if (v >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toFixed(0)
}

onMounted(async () => {
  await loadGroups()
  if (activeGroupId.value) {
    await loadStocks()
    await loadQuotes()
    startPolling()
  }
})

onUnmounted(stopPolling)
</script>

<template>
  <ToastNotify :show="toast.show" :message="toast.msg" :type="toast.type" />

  <div class="flex gap-6 h-full">
    <!-- 左侧：分组 -->
    <div class="w-52 shrink-0">
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden sticky top-4">
        <div class="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <span class="text-sm font-semibold text-gray-700">分组列表</span>
          <button @click="createGroup" class="text-indigo-600 hover:text-indigo-800 text-lg leading-none" title="新建分组">+</button>
        </div>
        <div class="divide-y divide-gray-50 max-h-[70vh] overflow-y-auto">
          <div v-for="g in groups" :key="g.id"
               class="px-3 py-2.5 flex items-center justify-between group cursor-pointer transition"
               :class="activeGroupId === g.id ? 'bg-indigo-50 border-l-2 border-l-indigo-500' : 'hover:bg-gray-50 border-l-2 border-l-transparent'"
               @click="activeGroupId = g.id">
            <div v-if="editingGroupId !== g.id" class="flex-1 min-w-0">
              <div class="text-sm font-medium truncate" :class="activeGroupId === g.id ? 'text-indigo-700' : 'text-gray-700'">{{ g.name }}</div>
              <div class="text-xs text-gray-400">{{ g.stock_count }} 只</div>
            </div>
            <input v-else :id="`rename-input-${g.id}`" v-model="editingName"
                   @keyup.enter="confirmRename" @blur="confirmRename" @click.stop
                   class="flex-1 text-sm border border-indigo-400 rounded px-2 py-1 focus:outline-none" />
            <div v-if="editingGroupId !== g.id" class="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition ml-1">
              <button @click.stop="startRename(g.id, g.name)" class="text-gray-400 hover:text-indigo-600 p-0.5" title="重命名">✏</button>
              <button v-if="groups.length > 1" @click.stop="doDeleteGroup(g.id)" class="text-gray-400 hover:text-red-500 p-0.5" title="删除">✕</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧：股票行情表格 -->
    <div class="flex-1 min-w-0">
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div class="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 class="text-base font-bold text-gray-900">
            {{ activeGroup?.name || '自选股' }}
            <span class="ml-2 text-sm font-normal text-gray-400">{{ stocks.length }} 只</span>
          </h2>
          <div class="flex items-center gap-3 text-xs text-gray-400">
            <span v-if="lastQuoteTime">行情更新: {{ lastQuoteTime }}</span>
            <span v-if="quotesLoading" class="text-indigo-500">刷新中…</span>
            <span class="inline-block w-2 h-2 rounded-full animate-pulse" :class="quotesLoading ? 'bg-indigo-500' : 'bg-green-500'"></span>
            <span>每5秒刷新</span>
          </div>
        </div>

        <div v-if="enrichedStocks.length" class="overflow-x-auto">
          <table class="w-full text-sm whitespace-nowrap">
            <thead class="bg-gray-50 text-left">
              <tr class="text-xs">
                <th class="px-3 py-2.5 font-semibold text-gray-600">代码</th>
                <th class="px-3 py-2.5 font-semibold text-gray-600">名称</th>
                <th class="px-3 py-2.5 font-semibold text-gray-600 text-right">最新价</th>
                <th class="px-3 py-2.5 font-semibold text-gray-600 text-right">涨跌幅</th>
                <th class="px-3 py-2.5 font-semibold text-gray-600 text-right">涨跌额</th>
                <th class="px-3 py-2.5 font-semibold text-gray-600 text-right">市盈率</th>
                <th class="px-3 py-2.5 font-semibold text-gray-600 text-right">市净率</th>
                <th class="px-3 py-2.5 font-semibold text-gray-600 text-right">成交量</th>
                <th class="px-3 py-2.5 font-semibold text-gray-600 text-right">成交额</th>
                <th class="px-3 py-2.5 font-semibold text-gray-600 text-right">换手率</th>
                <th class="px-3 py-2.5 font-semibold text-gray-600 text-right">量比</th>
                <th class="px-3 py-2.5 font-semibold text-gray-600 text-right">总市值</th>
                <th class="px-3 py-2.5 font-semibold text-gray-600">市场</th>
                <th class="px-3 py-2.5 font-semibold text-gray-600 text-center">操作</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="s in enrichedStocks" :key="s.id"
                  class="hover:bg-gray-50 transition group">
                <td class="px-3 py-2.5 font-mono text-xs text-gray-700">{{ s.symbol }}</td>
                <td class="px-3 py-2.5 font-medium text-gray-900">{{ s.quote?.name || s.stock_name || '-' }}</td>

                <!-- 最新价 -->
                <td class="px-3 py-2.5 text-right font-semibold"
                    :class="(s.quote?.change_pct ?? 0) > 0 ? 'text-red-600' : (s.quote?.change_pct ?? 0) < 0 ? 'text-green-600' : 'text-gray-800'">
                  {{ s.quote?.current_price ? s.quote.current_price.toFixed(2) : '-' }}
                </td>

                <!-- 涨跌幅 -->
                <td class="px-3 py-2.5 text-right font-semibold"
                    :class="(s.quote?.change_pct ?? 0) > 0 ? 'text-red-600' : (s.quote?.change_pct ?? 0) < 0 ? 'text-green-600' : 'text-gray-500'">
                  <template v-if="s.quote?.change_pct != null">
                    {{ (s.quote.change_pct > 0 ? '+' : '') + s.quote.change_pct.toFixed(2) }}%
                  </template>
                  <template v-else>-</template>
                </td>

                <!-- 涨跌额 -->
                <td class="px-3 py-2.5 text-right"
                    :class="(s.quote?.change_amount ?? 0) > 0 ? 'text-red-500' : (s.quote?.change_amount ?? 0) < 0 ? 'text-green-500' : 'text-gray-400'">
                  {{ s.quote?.change_amount ? ((s.quote.change_amount > 0 ? '+' : '') + s.quote.change_amount.toFixed(2)) : '-' }}
                </td>

                <!-- 市盈率 -->
                <td class="px-3 py-2.5 text-right text-gray-700">
                  {{ s.quote?.pe_ratio ? s.quote.pe_ratio.toFixed(2) : '-' }}
                </td>

                <!-- 市净率 -->
                <td class="px-3 py-2.5 text-right text-gray-700">
                  {{ s.quote?.pb_ratio ? s.quote.pb_ratio.toFixed(2) : '-' }}
                </td>

                <!-- 成交量 -->
                <td class="px-3 py-2.5 text-right text-gray-600">{{ s.quote ? fmtVol(s.quote.volume) : '-' }}</td>

                <!-- 成交额 -->
                <td class="px-3 py-2.5 text-right text-gray-600">{{ s.quote ? fmtVol(s.quote.turnover) : '-' }}</td>

                <!-- 换手率 -->
                <td class="px-3 py-2.5 text-right text-gray-600">
                  {{ s.quote?.turnover_rate ? s.quote.turnover_rate.toFixed(2) + '%' : '-' }}
                </td>

                <!-- 量比 -->
                <td class="px-3 py-2.5 text-right text-gray-600">
                  {{ s.quote?.volume_ratio ? s.quote.volume_ratio.toFixed(2) : '-' }}
                </td>

                <!-- 总市值 -->
                <td class="px-3 py-2.5 text-right text-gray-600">{{ s.quote ? fmtCap(s.quote.total_market_cap) : '-' }}</td>

                <!-- 市场 -->
                <td class="px-3 py-2.5">
                  <span v-if="s.market" class="text-xs px-1.5 py-0.5 rounded" :class="marketCls(s.market)">{{ s.market }}</span>
                </td>

                <!-- 操作 -->
                <td class="px-3 py-2.5 text-center">
                  <div class="flex items-center justify-center gap-1 opacity-70 group-hover:opacity-100 transition">
                    <button @click="goAnalyze(s.symbol)" class="text-xs text-indigo-600 hover:text-indigo-800">分析</button>
                    <button @click="doRemoveStock(s.id)" class="text-xs text-red-500 hover:text-red-700">移除</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else-if="!loading" class="p-16 text-center text-gray-400">
          <svg class="w-14 h-14 mx-auto mb-3" fill="none" stroke="currentColor" stroke-width="1" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z"/>
          </svg>
          <p class="text-sm">暂无自选股</p>
          <p class="text-xs mt-1">在其他页面的股票结果中点击 ☆自选 按钮添加</p>
        </div>
      </div>
    </div>
  </div>
</template>
