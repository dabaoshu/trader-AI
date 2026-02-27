<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { fetchWatchlistGroups, addWatchlistStock } from '../api'
import type { WatchlistGroup } from '../types'

const props = defineProps<{
  symbol: string
  stockName?: string
  market?: string
}>()

const emit = defineEmits<{ (e: 'added'): void }>()

const groups = ref<WatchlistGroup[]>([])
const open = ref(false)
const loading = ref(false)
const message = ref('')

async function loadGroups() {
  const res = await fetchWatchlistGroups()
  if (res.success) groups.value = res.data
}

async function addTo(groupId: number) {
  loading.value = true
  message.value = ''
  try {
    const res = await addWatchlistStock(groupId, {
      symbol: props.symbol,
      stock_name: props.stockName || '',
      market: props.market || '',
    })
    if (res.success) {
      message.value = '✓ 已添加'
      emit('added')
      setTimeout(() => { open.value = false; message.value = '' }, 800)
    } else {
      message.value = res.message || '添加失败'
    }
  } finally {
    loading.value = false
  }
}

function toggle() {
  open.value = !open.value
  if (open.value) loadGroups()
}
</script>

<template>
  <div class="relative inline-block">
    <button @click.stop="toggle"
            class="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-md border border-amber-300 text-amber-700 bg-amber-50 hover:bg-amber-100 transition"
            title="添加到自选股">
      <span class="text-sm leading-none">☆</span>
      <span>自选</span>
    </button>

    <!-- Dropdown -->
    <div v-if="open"
         class="absolute right-0 top-full mt-1 z-50 w-48 bg-white rounded-lg shadow-xl border border-gray-200 overflow-hidden">
      <div class="px-3 py-2 border-b border-gray-100 text-xs font-semibold text-gray-500">添加到分组</div>
      <div class="max-h-48 overflow-y-auto">
        <button v-for="g in groups" :key="g.id" @click.stop="addTo(g.id)" :disabled="loading"
                class="w-full text-left px-3 py-2 text-sm hover:bg-indigo-50 transition flex items-center justify-between disabled:opacity-50">
          <span>{{ g.name }}</span>
          <span class="text-xs text-gray-400">{{ g.stock_count }}只</span>
        </button>
      </div>
      <div v-if="message" class="px-3 py-2 text-xs text-center border-t border-gray-100"
           :class="message.startsWith('✓') ? 'text-green-600' : 'text-red-500'">{{ message }}</div>
      <div v-if="!groups.length" class="px-3 py-4 text-center text-xs text-gray-400">暂无分组</div>
    </div>
  </div>
</template>
