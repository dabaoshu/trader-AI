<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import {
  fetchWatchlistGroups, addWatchlistGroup, renameWatchlistGroup,
  deleteWatchlistGroup, fetchWatchlistStocks, removeWatchlistStock,
} from '../api'
import type { WatchlistGroup, WatchlistStock } from '../types'
import ToastNotify from '../components/ToastNotify.vue'
import AddToWatchlist from '../components/AddToWatchlist.vue'

const groups = ref<WatchlistGroup[]>([])
const activeGroupId = ref<number | null>(null)
const stocks = ref<WatchlistStock[]>([])
const loading = ref(false)
const toast = ref({ show: false, msg: '', type: 'info' })

const editingGroupId = ref<number | null>(null)
const editingName = ref('')
const addingSymbol = ref('')

function notify(msg: string, type = 'info') {
  toast.value = { show: true, msg, type }
  setTimeout(() => (toast.value.show = false), 3000)
}

const activeGroup = computed(() => groups.value.find(g => g.id === activeGroupId.value))

async function loadGroups() {
  const res = await fetchWatchlistGroups()
  if (res.success) {
    groups.value = res.data
    if (!activeGroupId.value && res.data.length) {
      activeGroupId.value = res.data[0].id
    }
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

watch(activeGroupId, () => loadStocks())

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
  if (!editingGroupId.value || !editingName.value.trim()) {
    editingGroupId.value = null; return
  }
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

function confidenceColor(c: string) {
  if (c === '上海主板') return 'bg-red-100 text-red-700'
  if (c === '深圳主板') return 'bg-blue-100 text-blue-700'
  if (c === '创业板') return 'bg-purple-100 text-purple-700'
  if (c === '中小板') return 'bg-amber-100 text-amber-700'
  return 'bg-gray-100 text-gray-600'
}

onMounted(async () => {
  await loadGroups()
  if (activeGroupId.value) await loadStocks()
})
</script>

<template>
  <ToastNotify :show="toast.show" :message="toast.msg" :type="toast.type" />

  <div class="flex gap-6 h-full">

    <!-- 左侧：分组 tabs -->
    <div class="w-56 shrink-0 space-y-2">
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div class="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <span class="text-sm font-semibold text-gray-700">分组列表</span>
          <button @click="createGroup" class="text-indigo-600 hover:text-indigo-800 text-lg leading-none" title="新建分组">+</button>
        </div>
        <div class="divide-y divide-gray-50">
          <div v-for="g in groups" :key="g.id"
               class="px-3 py-2.5 flex items-center justify-between group cursor-pointer transition"
               :class="activeGroupId === g.id ? 'bg-indigo-50 border-l-2 border-l-indigo-500' : 'hover:bg-gray-50 border-l-2 border-l-transparent'"
               @click="activeGroupId = g.id">

            <!-- 正常态 -->
            <div v-if="editingGroupId !== g.id" class="flex-1 min-w-0">
              <div class="text-sm font-medium truncate" :class="activeGroupId === g.id ? 'text-indigo-700' : 'text-gray-700'">
                {{ g.name }}
              </div>
              <div class="text-xs text-gray-400">{{ g.stock_count }} 只</div>
            </div>

            <!-- 编辑态 -->
            <input v-else
                   :id="`rename-input-${g.id}`"
                   v-model="editingName"
                   @keyup.enter="confirmRename"
                   @blur="confirmRename"
                   @click.stop
                   class="flex-1 text-sm border border-indigo-400 rounded px-2 py-1 focus:outline-none" />

            <!-- 操作 -->
            <div v-if="editingGroupId !== g.id" class="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition ml-1">
              <button @click.stop="startRename(g.id, g.name)" class="text-gray-400 hover:text-indigo-600 p-0.5" title="重命名">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z"/></svg>
              </button>
              <button v-if="groups.length > 1" @click.stop="doDeleteGroup(g.id)" class="text-gray-400 hover:text-red-500 p-0.5" title="删除">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
          </div>
        </div>
        <div v-if="!groups.length" class="p-6 text-center text-gray-400 text-xs">暂无分组</div>
      </div>
    </div>

    <!-- 右侧：股票列表 -->
    <div class="flex-1 min-w-0">
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div class="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 class="text-base font-bold text-gray-900">
            {{ activeGroup?.name || '自选股' }}
            <span class="ml-2 text-sm font-normal text-gray-400">{{ stocks.length }} 只</span>
          </h2>
        </div>

        <!-- 股票表格 -->
        <div v-if="stocks.length" class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 text-left">
              <tr>
                <th class="px-5 py-3 font-semibold text-gray-600">代码</th>
                <th class="px-5 py-3 font-semibold text-gray-600">名称</th>
                <th class="px-5 py-3 font-semibold text-gray-600">市场</th>
                <th class="px-5 py-3 font-semibold text-gray-600">添加时间</th>
                <th class="px-5 py-3 font-semibold text-gray-600 text-center">操作</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="s in stocks" :key="s.id" class="hover:bg-gray-50 transition">
                <td class="px-5 py-3 font-mono text-gray-800">{{ s.symbol }}</td>
                <td class="px-5 py-3 font-medium text-gray-900">{{ s.stock_name || '-' }}</td>
                <td class="px-5 py-3">
                  <span v-if="s.market" class="text-xs px-2 py-0.5 rounded" :class="confidenceColor(s.market)">{{ s.market }}</span>
                  <span v-else class="text-gray-400">-</span>
                </td>
                <td class="px-5 py-3 text-gray-500 text-xs">{{ s.added_at }}</td>
                <td class="px-5 py-3 text-center">
                  <button @click="doRemoveStock(s.id)" class="text-red-500 hover:text-red-700 text-xs">移除</button>
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
