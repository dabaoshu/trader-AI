/**
 * @file 选股记录管理后台 API 封装
 */

const BASE = '/api/screener'

/**
 * @param {number} limit
 * @returns {Promise<{success:boolean, data:Array}>}
 */
export async function fetchRecords(limit = 50) {
  const res = await fetch(`${BASE}/records?limit=${limit}`)
  return res.json()
}

/**
 * @param {number} id
 * @returns {Promise<{success:boolean, data:object}>}
 */
export async function fetchRecordDetail(id) {
  const res = await fetch(`${BASE}/records/${id}`)
  return res.json()
}

/**
 * @param {number} id
 * @returns {Promise<{success:boolean}>}
 */
export async function deleteRecord(id) {
  const res = await fetch(`${BASE}/records/${id}`, { method: 'DELETE' })
  return res.json()
}

/**
 * @returns {Promise<{success:boolean, data:Array}>}
 */
export async function fetchPresets() {
  const res = await fetch(`${BASE}/presets`)
  return res.json()
}

/**
 * @param {object} payload - { name, conditions, preset_key }
 * @returns {Promise<{success:boolean, data:object}>}
 */
export async function runScreener(payload) {
  const res = await fetch(`${BASE}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return res.json()
}
