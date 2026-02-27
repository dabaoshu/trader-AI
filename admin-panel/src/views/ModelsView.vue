<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  fetchProviders, addProvider, updateProvider, deleteProvider,
  setDefaultProvider, testProvider, fetchCallers, setCallerProvider,
} from '../api'
import type { AIProvider, CallerItem } from '../types'
import ToastNotify from '../components/ToastNotify.vue'

const providers = ref<AIProvider[]>([])
const defaultProviderId = ref('')
const callers = ref<CallerItem[]>([])
const toast = ref({ show: false, msg: '', type: 'info' })
const testing = ref<Record<string, boolean>>({})

const showAdd = ref(false)
const editingId = ref<string | null>(null)
const form = ref({ name: '', base_url: '', model_id: '', api_key: '' })
const showKey = ref<Record<string, boolean>>({})

function notify(msg: string, type = 'info') {
  toast.value = { show: true, msg, type }
  setTimeout(() => (toast.value.show = false), 3000)
}

async function load() {
  const pRes = await fetchProviders()
  if (pRes.success) {
    providers.value = pRes.data.providers
    defaultProviderId.value = pRes.data.default_provider_id
  }
  const cRes = await fetchCallers()
  if (cRes.success) callers.value = cRes.data
}

function startAdd() {
  form.value = { name: '', base_url: '', model_id: '', api_key: '' }
  editingId.value = null
  showAdd.value = true
}

function startEdit(p: AIProvider) {
  form.value = { name: p.name, base_url: p.base_url, model_id: p.model_id, api_key: p.api_key }
  editingId.value = p.id
  showAdd.value = true
}

function cancelEdit() {
  showAdd.value = false
  editingId.value = null
}

async function saveProvider() {
  if (!form.value.base_url || !form.value.model_id) {
    notify('请填写基础 URL 和模型 ID', 'error'); return
  }
  if (editingId.value) {
    const res = await updateProvider(editingId.value, form.value)
    if (res.success) notify('已更新', 'success')
  } else {
    const res = await addProvider(form.value)
    if (res.success) notify('已添加', 'success')
  }
  showAdd.value = false
  editingId.value = null
  await load()
}

async function removeProvider(id: string) {
  if (!confirm('确定删除此提供商？')) return
  await deleteProvider(id)
  notify('已删除', 'success')
  await load()
}

async function doSetDefault(id: string) {
  await setDefaultProvider(id)
  defaultProviderId.value = id
  notify('已设为默认', 'success')
}

async function doTest(id: string) {
  testing.value[id] = true
  try {
    const res = await testProvider(id)
    notify(res.message, res.success ? 'success' : 'error')
  } finally {
    testing.value[id] = false
  }
}

async function onCallerChange(callerId: string, providerId: string) {
  await setCallerProvider(callerId, providerId)
  notify('调用者绑定已更新', 'success')
}

function maskKey(key: string): string {
  if (!key) return ''
  if (key.length <= 8) return '****'
  return key.slice(0, 4) + '****' + key.slice(-4)
}

onMounted(load)
</script>

<template>
  <ToastNotify :show="toast.show" :message="toast.msg" :type="toast.type" />

  <div class="space-y-6">

    <!-- 提供商管理 -->
    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div class="px-6 py-5 border-b border-gray-200 flex items-center justify-between">
        <div>
          <h2 class="text-base font-bold text-gray-900 flex items-center gap-2">
            <svg class="w-5 h-5 text-indigo-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" />
            </svg>
            AI 模型提供商
          </h2>
          <p class="text-xs text-gray-500 mt-1">配置 AI 模型提供商和 API 密钥</p>
        </div>
        <button @click="startAdd"
                class="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 transition">
          <span class="text-lg leading-none">+</span> 添加提供商
        </button>
      </div>

      <div class="divide-y divide-gray-100">
        <!-- 添加/编辑表单 -->
        <div v-if="showAdd" class="p-6 bg-indigo-50/50 border-2 border-indigo-200 m-4 rounded-xl">
          <div class="flex items-center gap-2 mb-4">
            <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            </svg>
            <div>
              <div class="text-sm font-bold text-gray-900">{{ editingId ? '编辑' : '自定义' }}</div>
              <div class="text-xs text-gray-400">Custom</div>
            </div>
          </div>

          <div class="space-y-3">
            <div>
              <label class="block text-xs font-medium text-gray-500 mb-1">名称</label>
              <input v-model="form.name" class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="如: MiniMax / OpenAI / DeepSeek" />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-500 mb-1">基础 URL</label>
              <input v-model="form.base_url" class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono" placeholder="https://api.minimaxi.com/v1" />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-500 mb-1">模型 ID</label>
              <input v-model="form.model_id" class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono" placeholder="MiniMax-M2.5" />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-500 mb-1">API Key</label>
              <input v-model="form.api_key" type="password" class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono" placeholder="API key..." />
            </div>
            <div class="flex items-center gap-2 pt-1">
              <button @click="saveProvider" class="px-4 py-1.5 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700">保存</button>
              <button @click="cancelEdit" class="px-4 py-1.5 text-gray-600 text-sm rounded-lg hover:bg-gray-100">取消</button>
            </div>
          </div>
        </div>

        <!-- 提供商列表 -->
        <div v-for="p in providers" :key="p.id" class="p-5 hover:bg-gray-50/50 transition">
          <div class="flex items-start justify-between">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-2">
                <div class="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-xs"
                     :class="p.enabled ? 'bg-indigo-600' : 'bg-gray-400'">
                  {{ p.name?.charAt(0)?.toUpperCase() || 'A' }}
                </div>
                <div>
                  <div class="text-sm font-semibold text-gray-900">{{ p.name }}</div>
                  <div class="text-xs text-gray-400 font-mono">{{ p.model_id }}</div>
                </div>
                <span v-if="p.id === defaultProviderId"
                      class="text-[10px] px-2 py-0.5 bg-green-100 text-green-700 rounded-full font-medium">默认</span>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 text-xs text-gray-500 ml-10">
                <div><span class="text-gray-400">URL:</span> <span class="font-mono">{{ p.base_url }}</span></div>
                <div class="flex items-center gap-1">
                  <span class="text-gray-400">Key:</span>
                  <span class="font-mono">{{ showKey[p.id] ? p.api_key : maskKey(p.api_key) }}</span>
                  <button @click="showKey[p.id] = !showKey[p.id]" class="text-gray-400 hover:text-gray-600">
                    {{ showKey[p.id] ? '🙈' : '👁' }}
                  </button>
                </div>
              </div>
            </div>

            <div class="flex items-center gap-1 shrink-0 ml-4">
              <button @click="doTest(p.id)" :disabled="testing[p.id]"
                      class="text-xs px-2.5 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 disabled:opacity-50 transition">
                {{ testing[p.id] ? '测试中…' : '测试' }}
              </button>
              <button v-if="p.id !== defaultProviderId" @click="doSetDefault(p.id)"
                      class="text-xs px-2.5 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 transition">
                设为默认
              </button>
              <button @click="startEdit(p)" class="text-xs px-2.5 py-1 text-indigo-600 hover:bg-indigo-50 rounded-lg transition">编辑</button>
              <button @click="removeProvider(p.id)" class="text-xs px-2.5 py-1 text-red-500 hover:bg-red-50 rounded-lg transition">删除</button>
            </div>
          </div>
        </div>

        <div v-if="!providers.length && !showAdd" class="p-12 text-center text-gray-400 text-sm">
          <p>暂无模型提供商</p>
          <p class="text-xs mt-1">点击右上角「添加提供商」开始配置</p>
        </div>
      </div>
    </div>

    <!-- 调用者绑定 -->
    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div class="px-6 py-5 border-b border-gray-200">
        <h2 class="text-base font-bold text-gray-900 flex items-center gap-2">
          <svg class="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
          </svg>
          调用者模型绑定
        </h2>
        <p class="text-xs text-gray-500 mt-1">为不同的功能模块指定使用的 AI 模型，未指定则使用默认模型</p>
      </div>

      <div class="divide-y divide-gray-100">
        <div v-for="c in callers" :key="c.caller_id" class="px-6 py-4 flex items-center justify-between">
          <div>
            <div class="text-sm font-medium text-gray-900">{{ c.label }}</div>
            <div class="text-xs text-gray-400 font-mono">{{ c.caller_id }}</div>
          </div>
          <select
            :value="c.provider_id"
            @change="onCallerChange(c.caller_id, ($event.target as HTMLSelectElement).value)"
            class="text-sm border border-gray-300 rounded-lg px-3 py-1.5 w-56 focus:outline-none focus:ring-2 focus:ring-indigo-500">
            <option value="">使用默认模型</option>
            <option v-for="p in providers" :key="p.id" :value="p.id">{{ p.name }} ({{ p.model_id }})</option>
          </select>
        </div>
      </div>
    </div>
  </div>
</template>
