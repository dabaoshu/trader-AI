import type {
  ApiResponse,
  ScreenerRecord,
  PresetTemplate,
  RunScreenerData,
  ScreenerConditions,
  AnalysisRule,
  AnalysisReport,
  AIProvider,
  CallerItem,
  WatchlistGroup,
  WatchlistStock,
} from './types'

const BASE = '/api/screener'

export async function fetchRecords(limit = 50): Promise<ApiResponse<ScreenerRecord[]>> {
  const res = await fetch(`${BASE}/records?limit=${limit}`)
  return res.json()
}

export async function fetchRecordDetail(id: number): Promise<ApiResponse<ScreenerRecord>> {
  const res = await fetch(`${BASE}/records/${id}`)
  return res.json()
}

export async function deleteRecord(id: number): Promise<ApiResponse> {
  const res = await fetch(`${BASE}/records/${id}`, { method: 'DELETE' })
  return res.json()
}

export async function fetchPresets(): Promise<ApiResponse<PresetTemplate[]>> {
  const res = await fetch(`${BASE}/presets`)
  return res.json()
}

export async function runScreener(payload: {
  name?: string
  conditions?: ScreenerConditions
  preset_key?: string
}): Promise<ApiResponse<RunScreenerData>> {
  const res = await fetch(`${BASE}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return res.json()
}

// ---- Analyzer API ----

export async function fetchAnalysisRules(): Promise<ApiResponse<AnalysisRule[]>> {
  const res = await fetch('/api/analyzer/rules')
  return res.json()
}

export async function analyzeStock(payload: {
  stock_code: string
  rule_ids?: string[]
}): Promise<ApiResponse<AnalysisReport>> {
  const res = await fetch('/api/analyzer/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return res.json()
}

// ---- AI Model Management ----

export async function fetchProviders(): Promise<ApiResponse<{ providers: AIProvider[]; default_provider_id: string }>> {
  const res = await fetch('/api/models/providers')
  return res.json()
}

export async function addProvider(data: Partial<AIProvider>): Promise<ApiResponse<AIProvider>> {
  const res = await fetch('/api/models/providers', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
  return res.json()
}

export async function updateProvider(id: string, data: Partial<AIProvider>): Promise<ApiResponse<AIProvider>> {
  const res = await fetch(`/api/models/providers/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
  return res.json()
}

export async function deleteProvider(id: string): Promise<ApiResponse> {
  const res = await fetch(`/api/models/providers/${id}`, { method: 'DELETE' })
  return res.json()
}

export async function setDefaultProvider(id: string): Promise<ApiResponse> {
  const res = await fetch(`/api/models/providers/${id}/default`, { method: 'POST' })
  return res.json()
}

export async function testProvider(id: string): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`/api/models/providers/${id}/test`, { method: 'POST' })
  return res.json()
}

export async function fetchCallers(): Promise<ApiResponse<CallerItem[]>> {
  const res = await fetch('/api/models/callers')
  return res.json()
}

export async function setCallerProvider(callerId: string, providerId: string): Promise<ApiResponse> {
  const res = await fetch(`/api/models/callers/${callerId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ provider_id: providerId }) })
  return res.json()
}

// ---- Watchlist API ----

export async function fetchWatchlistGroups(): Promise<ApiResponse<WatchlistGroup[]>> {
  const res = await fetch('/api/watchlist/groups')
  return res.json()
}

export async function addWatchlistGroup(name: string): Promise<ApiResponse<WatchlistGroup>> {
  const res = await fetch('/api/watchlist/groups', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) })
  return res.json()
}

export async function renameWatchlistGroup(id: number, name: string): Promise<ApiResponse> {
  const res = await fetch(`/api/watchlist/groups/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) })
  return res.json()
}

export async function deleteWatchlistGroup(id: number): Promise<ApiResponse> {
  const res = await fetch(`/api/watchlist/groups/${id}`, { method: 'DELETE' })
  return res.json()
}

export async function fetchWatchlistStocks(groupId: number): Promise<ApiResponse<WatchlistStock[]>> {
  const res = await fetch(`/api/watchlist/groups/${groupId}/stocks`)
  return res.json()
}

export async function addWatchlistStock(groupId: number, data: { symbol: string; stock_name?: string; market?: string }): Promise<ApiResponse<WatchlistStock>> {
  const res = await fetch(`/api/watchlist/groups/${groupId}/stocks`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
  return res.json()
}

export async function removeWatchlistStock(stockId: number): Promise<ApiResponse> {
  const res = await fetch(`/api/watchlist/stocks/${stockId}`, { method: 'DELETE' })
  return res.json()
}
