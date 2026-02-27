/** 自定义筛选规则 */
export interface CustomRule {
  field: string
  op: 'gt' | 'gte' | 'lt' | 'lte' | 'eq' | 'neq' | 'contains'
  value: string | number
}

/** 筛选条件 */
export interface ScreenerConditions {
  price_min?: number
  price_max?: number
  total_score_min?: number
  total_score_max?: number
  tech_score_min?: number
  tech_score_max?: number
  auction_score_min?: number
  auction_score_max?: number
  auction_ratio_min?: number
  auction_ratio_max?: number
  rsi_min?: number
  rsi_max?: number
  market_cap_min?: number
  market_cap_max?: number
  gap_types?: string[]
  confidence_levels?: string[]
  markets?: string[]
  keyword?: string
  custom_rules?: CustomRule[]
  _preset_key?: string
}

/** 股票数据 */
export interface StockItem {
  symbol: string
  stock_name: string
  market: string
  current_price: number
  total_score: number
  tech_score: number
  auction_score: number
  auction_ratio: number
  gap_type: string
  confidence: 'very_high' | 'high' | 'medium'
  strategy: string
  entry_price: number
  stop_loss: number
  target_price: number
  rsi?: number
  market_cap_billion?: number
}

/** 结果摘要 */
export interface ResultSummary {
  count: number
  avg_score: number
  high_confidence_count: number
  markets: string[]
  price_range: [number, number]
  top_stocks: StockItem[]
}

/** 选股记录 */
export interface ScreenerRecord {
  id: number
  name: string
  conditions: ScreenerConditions
  result_count: number
  result_symbols: string[]
  result_summary: ResultSummary
  result_data?: StockItem[]
  preset_key: string
  created_at: string
}

/** 预置模板 */
export interface PresetTemplate {
  key: string
  name: string
  description: string
  conditions: ScreenerConditions
}

/** 通用 API 响应 */
export interface ApiResponse<T = unknown> {
  success: boolean
  message?: string
  data: T
}

/** 执行选股响应 data */
export interface RunScreenerData {
  record_id: number
  total: number
  stocks: StockItem[]
}

/** 字段选项 */
export interface FieldOption {
  value: string
  label: string
}

/** 操作符选项 */
export interface OpOption {
  value: CustomRule['op']
  label: string
}

// ---- Watchlist types ----

/** 自选股分组 */
export interface WatchlistGroup {
  id: number
  name: string
  sort_order: number
  stock_count: number
  created_at?: string
}

/** 自选股票 */
export interface WatchlistStock {
  id: number
  group_id: number
  symbol: string
  stock_name: string
  market: string
  note: string
  added_at: string
}

/** 实时行情数据 */
export interface RealtimeQuote {
  symbol: string
  name: string
  current_price: number
  change_pct: number
  change_amount: number
  pe_ratio: number
  pb_ratio: number
  volume: number
  turnover: number
  turnover_rate: number
  volume_ratio: number
  high: number
  low: number
  open: number
  prev_close: number
  total_market_cap: number
  circulating_market_cap: number
  updated_at: string
}

// ---- AI Model types ----

/** AI 模型提供商 */
export interface AIProvider {
  id: string
  name: string
  base_url: string
  model_id: string
  api_key: string
  enabled: boolean
  created_at: string
}

/** 调用者映射项 */
export interface CallerItem {
  caller_id: string
  label: string
  provider_id: string
}

// ---- Analyzer types ----

/** 分析规则元信息 */
export interface AnalysisRule {
  rule_id: string
  name: string
  description: string
  weight: number
}

/** 单条规则结果 */
export interface RuleResult {
  name: string
  score: number
  weight: number
  details: string
}

/** 分析报告 */
export interface AnalysisReport {
  stock_code: string
  stock_name: string
  market: string
  market_label: string
  currency: string
  analysis_date: string
  price_info: {
    current_price: number
    price_change: number
    volume_ratio: number
  }
  technical: Record<string, unknown>
  rule_results: Record<string, RuleResult>
  comprehensive_score: number
  recommendation: string
  active_rules: string[]
  error?: string
}
