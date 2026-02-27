<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import {
  fetchRecords,
  fetchRecordDetail,
  deleteRecord as apiDelete,
  fetchPresets,
  runScreener,
} from '../api'
import type { ScreenerRecord, PresetTemplate, ScreenerConditions } from '../types'
import ToastNotify from '../components/ToastNotify.vue'
import AddToWatchlist from '../components/AddToWatchlist.vue'

const records = ref<ScreenerRecord[]>([])
const presets = ref<PresetTemplate[]>([])
const loading = ref(false)
const detail = ref<ScreenerRecord | null>(null)
const showDetail = ref(false)
const searchQuery = ref('')
const toast = ref<{ show: boolean; msg: string; type: string }>({ show: false, msg: '', type: 'info' })

const filteredRecords = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return records.value
  return records.value.filter(
    (r) =>
      r.name.toLowerCase().includes(q) ||
      (r.preset_key || '').toLowerCase().includes(q) ||
      String(r.id).includes(q),
  )
})

function notify(msg: string, type = 'info') {
  toast.value = { show: true, msg, type }
  setTimeout(() => (toast.value.show = false), 3000)
}

async function loadRecords() {
  loading.value = true
  try {
    const res = await fetchRecords(100)
    if (res.success) records.value = res.data
  } finally {
    loading.value = false
  }
}

async function loadPresets() {
  const res = await fetchPresets()
  if (res.success) presets.value = res.data
}

async function viewDetail(id: number) {
  const res = await fetchRecordDetail(id)
  if (res.success) {
    detail.value = res.data
    showDetail.value = true
  }
}

async function removeRecord(id: number) {
  if (!confirm('确定删除此记录？')) return
  const res = await apiDelete(id)
  if (res.success) {
    notify('删除成功', 'success')
    await loadRecords()
    if (detail.value && detail.value.id === id) showDetail.value = false
  } else {
    notify(res.message || '删除失败', 'error')
  }
}

async function quickScreen(presetKey: string) {
  loading.value = true
  try {
    const res = await runScreener({ preset_key: presetKey })
    if (res.success) {
      notify(res.message ?? '选股完成', 'success')
      await loadRecords()
    } else {
      notify(res.message ?? '失败', 'error')
    }
  } finally {
    loading.value = false
  }
}

function conditionLabel(conditions: ScreenerConditions): string {
  const parts: string[] = []
  if (conditions.price_min != null || conditions.price_max != null) {
    parts.push(`价格 ${conditions.price_min ?? ''}~${conditions.price_max ?? ''}`)
  }
  if (conditions.total_score_min != null) parts.push(`评分≥${conditions.total_score_min}`)
  if (conditions.confidence_levels) parts.push(conditions.confidence_levels.join('/'))
  if (conditions.markets) parts.push(conditions.markets.join('/'))
  if (conditions.custom_rules && conditions.custom_rules.length) {
    parts.push(`自定义×${conditions.custom_rules.length}`)
  }
  return parts.length ? parts.join(' | ') : '无特定条件'
}

function confidenceTag(c: string): string {
  const map: Record<string, string> = { very_high: '非常高', high: '高', medium: '中等' }
  return map[c] || c
}

function confidenceColor(c: string): string {
  if (c === 'very_high') return 'bg-green-100 text-green-800'
  if (c === 'high') return 'bg-blue-100 text-blue-800'
  return 'bg-gray-100 text-gray-700'
}

onMounted(() => {
  loadRecords()
  loadPresets()
})
</script>

<template>
  <ToastNotify :show="toast.show" :message="toast.msg" :type="toast.type" />

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <!-- 左侧 -->
    <section class="lg:col-span-2 space-y-4">
      <!-- 快捷 -->
      <div class="bg-white rounded-xl border border-gray-200 p-5">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-sm font-semibold text-gray-700">快捷选股</h2>
          <div class="flex items-center gap-2">
            <input v-model="searchQuery" type="text" placeholder="搜索记录…"
                   class="text-sm border border-gray-300 rounded-lg px-3 py-1.5 w-44 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            <button @click="loadRecords" class="text-xs px-3 py-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">刷新</button>
          </div>
        </div>
        <div class="flex flex-wrap gap-2">
          <button v-for="p in presets" :key="p.key" @click="quickScreen(p.key)" :disabled="loading"
                  class="text-xs px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-lg hover:bg-indigo-100 disabled:opacity-50 transition">
            {{ p.name }}
          </button>
        </div>
      </div>

      <!-- 统计 -->
      <div class="grid grid-cols-3 gap-4">
        <div class="bg-white rounded-xl border border-gray-200 p-4 text-center">
          <div class="text-2xl font-bold text-indigo-600">{{ records.length }}</div>
          <div class="text-xs text-gray-500 mt-1">总记录</div>
        </div>
        <div class="bg-white rounded-xl border border-gray-200 p-4 text-center">
          <div class="text-2xl font-bold text-green-600">{{ records.reduce((s, r) => s + r.result_count, 0) }}</div>
          <div class="text-xs text-gray-500 mt-1">累计筛选股票</div>
        </div>
        <div class="bg-white rounded-xl border border-gray-200 p-4 text-center">
          <div class="text-2xl font-bold text-amber-600">{{ records.filter(r => r.preset_key).length }}</div>
          <div class="text-xs text-gray-500 mt-1">模板选股</div>
        </div>
      </div>

      <!-- 列表 -->
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-left">
            <tr>
              <th class="px-4 py-3 font-semibold text-gray-600">ID</th>
              <th class="px-4 py-3 font-semibold text-gray-600">名称</th>
              <th class="px-4 py-3 font-semibold text-gray-600">条件摘要</th>
              <th class="px-4 py-3 font-semibold text-gray-600 text-center">结果数</th>
              <th class="px-4 py-3 font-semibold text-gray-600">时间</th>
              <th class="px-4 py-3 font-semibold text-gray-600 text-center">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-if="loading && !filteredRecords.length"><td colspan="6" class="text-center py-12 text-gray-400">加载中…</td></tr>
            <tr v-else-if="!filteredRecords.length"><td colspan="6" class="text-center py-12 text-gray-400">暂无记录</td></tr>
            <tr v-for="r in filteredRecords" :key="r.id" class="hover:bg-gray-50 transition cursor-pointer" @click="viewDetail(r.id)">
              <td class="px-4 py-3 text-gray-500">#{{ r.id }}</td>
              <td class="px-4 py-3 font-medium text-gray-900">
                {{ r.name }}
                <span v-if="r.preset_key" class="ml-1 text-xs bg-indigo-100 text-indigo-600 px-1.5 py-0.5 rounded">{{ r.preset_key }}</span>
              </td>
              <td class="px-4 py-3 text-gray-500 text-xs max-w-xs truncate">{{ conditionLabel(r.conditions) }}</td>
              <td class="px-4 py-3 text-center">
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold"
                      :class="r.result_count > 0 ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'">{{ r.result_count }} 只</span>
              </td>
              <td class="px-4 py-3 text-gray-500 text-xs">{{ r.created_at }}</td>
              <td class="px-4 py-3 text-center" @click.stop>
                <button @click="viewDetail(r.id)" class="text-indigo-600 hover:text-indigo-800 text-xs mr-2">详情</button>
                <button @click="removeRecord(r.id)" class="text-red-500 hover:text-red-700 text-xs">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 右侧详情 -->
    <aside>
      <div v-if="!showDetail" class="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
        <svg class="w-12 h-12 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293L16 6h2a2 2 0 012 2v11a2 2 0 01-2 2z"/>
        </svg>
        <p class="text-sm">点击左侧记录查看详情</p>
      </div>
      <div v-else class="bg-white rounded-xl border border-gray-200 overflow-hidden sticky top-4">
        <div class="p-4 border-b border-gray-200 flex items-center justify-between">
          <h3 class="font-semibold text-gray-900">#{{ detail!.id }} {{ detail!.name }}</h3>
          <button @click="showDetail = false" class="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <div class="p-4 border-b border-gray-100 bg-gray-50">
          <h4 class="text-xs font-semibold text-gray-500 mb-2">筛选条件</h4>
          <pre class="text-xs text-gray-700 bg-white rounded p-3 overflow-x-auto max-h-40 border border-gray-200">{{ JSON.stringify(detail!.conditions, null, 2) }}</pre>
        </div>
        <div class="p-4 border-b border-gray-100">
          <h4 class="text-xs font-semibold text-gray-500 mb-2">统计摘要</h4>
          <div class="grid grid-cols-2 gap-2 text-xs">
            <div><span class="text-gray-500">结果数:</span> <span class="font-semibold">{{ detail!.result_count }}</span></div>
            <div><span class="text-gray-500">平均分:</span> <span class="font-semibold">{{ detail!.result_summary?.avg_score ?? '-' }}</span></div>
            <div><span class="text-gray-500">强推:</span> <span class="font-semibold">{{ detail!.result_summary?.high_confidence_count ?? 0 }}</span></div>
            <div><span class="text-gray-500">时间:</span> <span class="font-semibold">{{ detail!.created_at }}</span></div>
          </div>
        </div>
        <div class="p-4">
          <h4 class="text-xs font-semibold text-gray-500 mb-2">完整结果 ({{ (detail!.result_data || []).length }} 只)</h4>
          <div class="space-y-2 max-h-80 overflow-y-auto">
            <div v-for="s in (detail!.result_data || [])" :key="s.symbol"
                 class="flex items-center justify-between border border-gray-100 rounded-lg p-2 text-xs hover:bg-gray-50">
              <div>
                <span class="font-mono text-gray-800">{{ s.symbol }}</span>
                <span class="ml-1 text-gray-500">{{ s.stock_name }}</span>
              </div>
              <div class="flex items-center gap-2">
                <span class="font-semibold">¥{{ (s.current_price ?? 0).toFixed(2) }}</span>
                <span class="px-1.5 py-0.5 rounded text-xs" :class="confidenceColor(s.confidence)">{{ confidenceTag(s.confidence) }}</span>
                <AddToWatchlist :symbol="s.symbol" :stock-name="s.stock_name" :market="s.market || ''" />
              </div>
            </div>
            <div v-if="!(detail!.result_data || []).length" class="text-center text-gray-400 py-4">
              无完整数据
            </div>
          </div>
        </div>
      </div>
    </aside>
  </div>
</template>
