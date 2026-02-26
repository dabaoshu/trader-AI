import type {
  ApiResponse,
  ScreenerRecord,
  PresetTemplate,
  RunScreenerData,
  ScreenerConditions,
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
