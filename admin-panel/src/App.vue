<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, RouterLink, RouterView } from 'vue-router'

const route = useRoute()

interface NavItem {
  to: string
  label: string
  icon: string
}

const navItems: NavItem[] = [
  { to: '/records', label: '选股记录', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2' },
  { to: '/screener', label: '条件选股', icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z' },
  { to: '/analyzer', label: '股票分析', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
]

const currentLabel = computed(() => navItems.find(n => route.path.startsWith(n.to))?.label ?? '')
</script>

<template>
  <div class="flex h-screen bg-gray-50">

    <!-- 侧边栏 -->
    <aside class="w-56 bg-white border-r border-gray-200 flex flex-col shrink-0">
      <div class="px-5 py-5 border-b border-gray-100">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">S</div>
          <div>
            <div class="text-sm font-bold text-gray-900 leading-tight">智能选股助手</div>
            <div class="text-[10px] text-gray-400">管理后台</div>
          </div>
        </div>
      </div>
      <nav class="flex-1 px-3 py-4 space-y-1">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
          :class="route.path.startsWith(item.to)
            ? 'bg-indigo-50 text-indigo-700'
            : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'"
        >
          <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
          </svg>
          {{ item.label }}
        </RouterLink>
      </nav>
      <div class="px-5 py-4 border-t border-gray-100 text-[10px] text-gray-400">
        Vue 3 + TypeScript + Vite
      </div>
    </aside>

    <!-- 主区域 -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <header class="bg-white border-b border-gray-200 px-6 py-4 shrink-0">
        <h1 class="text-lg font-bold text-gray-900">{{ currentLabel }}</h1>
      </header>
      <main class="flex-1 overflow-y-auto p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
