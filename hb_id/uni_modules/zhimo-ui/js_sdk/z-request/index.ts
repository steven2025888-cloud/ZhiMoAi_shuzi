import { inject, getCurrentInstance } from 'vue'

/**
 * z-request (uni-app Vue3)
 * - zero dependency
 * - based on uni.request / uni.uploadFile / uni.downloadFile
 *
 * Features:
 * - multi-platform (App/H5/MP)
 * - token injection
 * - interceptors
 * - dedupe (reuse / cancel-prev / reject)
 * - retry (supports exponential backoff)
 * - cache (GET + TTL)
 * - cancel request
 * - concurrency queue + priority
 * - mock (built-in)
 * - metrics & log store
 * - upload/download + progress
 * - debug mode
 */

export type ZAnyObj = Record<string, any>

export type HttpMethod =
  | 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  | 'HEAD' | 'OPTIONS'

export type DedupeStrategy = 'reuse' | 'cancel-prev' | 'reject'

export type PriorityLevel = 'high' | 'normal' | 'low'
export type Priority = number | PriorityLevel

export interface CacheOptions {
  enabled?: boolean
  /** GET 缓存 TTL（ms） */
  ttl?: number
  /** 仅在 method=GET 时生效 */
  include?: RegExp | ((ctx: RequestContext) => boolean)
  /** 自定义缓存 key */
  key?: (ctx: RequestContext) => string
}

export interface LoggerOptions {
  enabled?: boolean
  level?: 'debug' | 'info' | 'warn' | 'error'
  /** 自定义输出函数 */
  print?: (level: string, ...args: any[]) => void
}

export type MockMatch = string | RegExp | ((ctx: RequestContext) => boolean)
export type MockHandler = (ctx: RequestContext) => any | Promise<any>

export interface MockRoute {
  match: MockMatch
  /** 优先于 match 的 method 过滤（可选） */
  method?: HttpMethod | HttpMethod[]
  /** 返回 data 或返回 { data, statusCode, header } */
  handler: MockHandler
  /** 单条路由的延迟（ms），不传则使用 mock.delay */
  delay?: number
}

export interface MockOptions {
  enabled?: boolean
  /** 默认延迟（ms） */
  delay?: number
  /** mock 路由规则 */
  routes?: MockRoute[]
  /** 命中 mock 时打印日志 */
  logHit?: boolean
}

export interface MetricsOptions {
  enabled?: boolean
  /** 采样率 0~1，默认 1 */
  sampleRate?: number
  /** 最大保留条数（滚动） */
  maxEntries?: number
  /** 每次请求完成都会触发（可用于上报） */
  onRecord?: (entry: MetricsEntry) => void
}

export interface LogStoreOptions {
  enabled?: boolean
  maxEntries?: number
}

export interface ZRequestConfig {
  baseURL?: string
  timeout?: number
  headers?: Record<string, string>

  /** token 可传字符串/同步函数/异步函数 */
  token?: string | (() => string | Promise<string>)
  tokenHeader?: string
  tokenPrefix?: string

  /** uni.showLoading/隐藏 */
  showLoading?: boolean
  loadingTitle?: string
  loadingDelay?: number

  /** 防重 */
  dedupe?: boolean
  dedupeStrategy?: DedupeStrategy

  /** 并发限制 */
  maxConcurrent?: number
  /** 默认优先级（队列） */
  defaultPriority?: Priority

  /** 重试次数（失败后） */
  retry?: number
  /** 重试间隔 ms 或回调（可实现指数退避） */
  retryDelay?: number | ((attempt: number, err: ZRequestError, ctx: RequestContext) => number)

  /** GET 缓存 */
  cache?: CacheOptions

  /** mock */
  mock?: MockOptions

  /** 性能监控 */
  metrics?: MetricsOptions

  /** 日志存储（可用于页面调试追踪） */
  logStore?: LogStoreOptions

  /** 调试模式（会强制开启 logger.enabled，并输出更详细信息） */
  debug?: boolean

  /** 统一错误处理（返回值会作为最终 reject 的 error） */
  onError?: (err: ZRequestError, ctx: RequestContext) => any

  /** 是否只返回 data */
  dataOnly?: boolean

  /** 判断是否成功 */
  validateStatus?: (statusCode: number) => boolean

  /** 日志输出（控制台） */
  logger?: LoggerOptions
}

export interface RequestOptions {
  header?: Record<string, string>
  params?: ZAnyObj
  /** 单次覆盖超时 */
  timeout?: number
  /** 单次覆盖 loading */
  showLoading?: boolean
  /** 单次防重 */
  dedupe?: boolean
  dedupeStrategy?: DedupeStrategy
  /** 取消控制器 */
  cancelController?: CancelController
  /** 单次重试配置 */
  retry?: number
  retryDelay?: number | ((attempt: number, err: ZRequestError, ctx: RequestContext) => number)
  /** 单次缓存 */
  cache?: CacheOptions
  /** 单次是否只返回 data */
  dataOnly?: boolean
  /** 请求优先级（队列） */
  priority?: Priority
  /** 单次 mock 开关（true=强制走 mock；false=禁用 mock；undefined=跟随全局） */
  mock?: boolean
}

export interface RequestContext {
  id: string
  url: string
  fullURL: string
  method: HttpMethod
  data?: any
  header: Record<string, string>
  timeout: number
  params?: ZAnyObj
  attempt: number
  startTime: number
  showLoading: boolean
  meta: ZAnyObj
}

export interface ZResponse<T = any> {
  data: T
  statusCode: number
  header: any
  cookies?: string[]
  errMsg: string
}

export interface ZRequestError extends Error {
  isZRequestError: true
  code:
    | 'CANCELLED'
    | 'TIMEOUT'
    | 'NETWORK'
    | 'HTTP'
    | 'REQUEST_FAIL'
    | 'UNKNOWN'
  statusCode?: number
  response?: ZResponse
  cause?: any
}

export type RequestInterceptor = (ctx: RequestContext) => RequestContext | Promise<RequestContext>
export type ResponseInterceptor = <T = any>(res: ZResponse<T>, ctx: RequestContext) => (ZResponse<T> | any) | Promise<ZResponse<T> | any>
export type ErrorInterceptor = (err: any, ctx: RequestContext) => any

export interface MetricsEntry {
  id: string
  method: HttpMethod
  url: string
  fullURL: string
  statusCode?: number
  ok: boolean
  cost: number
  attempt: number
  startTime: number
  endTime: number
  fromCache?: boolean
  mocked?: boolean
  errorCode?: ZRequestError['code']
}

export interface MetricsSnapshot {
  total: number
  success: number
  error: number
  avg: number
  min: number
  max: number
  p50: number
  p95: number
  last?: MetricsEntry
}

export interface LogEntry {
  time: number
  id: string
  level: 'debug'|'info'|'warn'|'error'
  msg: string
  ctx?: Partial<RequestContext>
  extra?: any
}

class InterceptorManager<T> {
  private handlers: Array<{ fulfilled: T; rejected?: any } | null> = []
  use(fulfilled: T, rejected?: any) {
    this.handlers.push({ fulfilled, rejected })
    return this.handlers.length - 1
  }
  eject(id: number) {
    if (this.handlers[id]) this.handlers[id] = null
  }
  forEach(fn: (h: { fulfilled: T; rejected?: any }) => void) {
    this.handlers.forEach((h) => h && fn(h))
  }
}

export class CancelController {
  private _aborted = false
  private _reason: any = null
  private _task: any = null

  get aborted() { return this._aborted }
  get reason() { return this._reason }

  /** 内部绑定 request task */
  _bind(task: any) {
    this._task = task
    if (this._aborted) {
      try { task.abort() } catch (_) {}
    }
  }

  abort(reason: any = 'cancelled') {
    this._aborted = true
    this._reason = reason
    if (this._task) {
      try { this._task.abort() } catch (_) {}
    }
  }
}

function uid() {
  return `${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`
}

function isPlainObject(v: any) {
  return Object.prototype.toString.call(v) === '[object Object]'
}

function deepMerge<T extends any>(target: T, ...sources: any[]): T {
  const out: any = isPlainObject(target) ? { ...target } : target
  for (const src of sources) {
    if (!src) continue
    for (const k of Object.keys(src)) {
      const v = src[k]
      if (v === undefined) continue
      if (isPlainObject(v) && isPlainObject(out[k])) out[k] = deepMerge(out[k], v)
      else out[k] = v
    }
  }
  return out
}

function encodeQuery(obj: any) {
  if (!obj) return ''
  const parts: string[] = []
  Object.keys(obj).forEach((k) => {
    const v = obj[k]
    if (v === undefined || v === null) return
    if (Array.isArray(v)) {
      v.forEach((iv) => parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(iv))}`))
    } else {
      parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    }
  })
  return parts.join('&')
}

function joinURL(baseURL: string, url: string) {
  if (!baseURL) return url
  if (/^https?:\/\//i.test(url)) return url
  if (baseURL.endsWith('/') && url.startsWith('/')) return baseURL + url.slice(1)
  if (!baseURL.endsWith('/') && !url.startsWith('/')) return baseURL + '/' + url
  return baseURL + url
}

function buildFullURL(baseURL: string, url: string, params?: ZAnyObj) {
  const u = joinURL(baseURL || '', url)
  const qs = encodeQuery(params)
  if (!qs) return u
  return u.includes('?') ? `${u}&${qs}` : `${u}?${qs}`
}

function makeError(code: ZRequestError['code'], message: string, extra?: Partial<ZRequestError>): ZRequestError {
  const err = new Error(message) as ZRequestError
  err.isZRequestError = true
  err.code = code
  if (extra) Object.assign(err, extra)
  return err
}

function now() { return Date.now() }

function defaultValidateStatus(statusCode: number) {
  return statusCode >= 200 && statusCode < 300
}

function toLoggerPrint(opt?: LoggerOptions) {
  const print = opt?.print || ((level: string, ...args: any[]) => {
    // eslint-disable-next-line no-console
    ;(console as any)[level] ? (console as any)[level](...args) : console.log(...args)
  })
  const enabled = opt?.enabled ?? false
  const levelRank: Record<string, number> = { debug: 10, info: 20, warn: 30, error: 40 }
  const min = levelRank[opt?.level || 'info'] || 20
  const should = (lv: string) => enabled && (levelRank[lv] || 20) >= min
  return { print, should }
}

/** 内存 GET 缓存 */
class SimpleCache {
  private store = new Map<string, { expire: number; value: any }>()
  get(key: string) {
    const it = this.store.get(key)
    if (!it) return undefined
    if (it.expire > 0 && Date.now() > it.expire) {
      this.store.delete(key)
      return undefined
    }
    return it.value
  }
  set(key: string, value: any, ttl: number) {
    const expire = ttl > 0 ? Date.now() + ttl : 0
    this.store.set(key, { expire, value })
  }
  delete(key: string) { this.store.delete(key) }
  clear() { this.store.clear() }
}

function priorityToNumber(p?: Priority): number {
  if (p === undefined || p === null) return 50
  if (typeof p === 'number') return p
  if (p === 'high') return 100
  if (p === 'low') return 0
  return 50
}

/** 带优先级的并发队列 */
class PrioritySemaphore {
  private max: number
  private active = 0
  private queue: Array<{ p: number; resolve: () => void }> = []

  constructor(max: number) {
    this.max = Math.max(1, max || 6)
  }

  async acquire(priority: number) {
    if (this.active < this.max && this.queue.length === 0) {
      this.active++
      return
    }
    await new Promise<void>((resolve) => {
      const it = { p: priority, resolve }
      // 按优先级从高到低插入（稳定）
      let i = 0
      while (i < this.queue.length && this.queue[i].p >= it.p) i++
      this.queue.splice(i, 0, it)
    })
    this.active++
  }

  release() {
    this.active = Math.max(0, this.active - 1)
    const next = this.queue.shift()
    if (next) next.resolve()
  }

  setMax(n: number) {
    this.max = Math.max(1, n || 6)
  }
}

/** 指标采集 */
class MetricsCollector {
  private opt: Required<MetricsOptions>
  private items: MetricsEntry[] = []

  constructor(opt?: MetricsOptions) {
    this.opt = {
      enabled: opt?.enabled ?? false,
      sampleRate: opt?.sampleRate ?? 1,
      maxEntries: opt?.maxEntries ?? 200,
      onRecord: opt?.onRecord ?? (() => {})
    }
  }

  setOptions(opt?: MetricsOptions) {
    this.opt = {
      enabled: opt?.enabled ?? this.opt.enabled,
      sampleRate: opt?.sampleRate ?? this.opt.sampleRate,
      maxEntries: opt?.maxEntries ?? this.opt.maxEntries,
      onRecord: opt?.onRecord ?? this.opt.onRecord
    }
  }

  record(entry: MetricsEntry) {
    if (!this.opt.enabled) return
    if (this.opt.sampleRate < 1 && Math.random() > this.opt.sampleRate) return
    this.items.push(entry)
    if (this.items.length > this.opt.maxEntries) this.items.splice(0, this.items.length - this.opt.maxEntries)
    try { this.opt.onRecord(entry) } catch (_) {}
  }

  clear() { this.items = [] }

  snapshot(): MetricsSnapshot {
    const list = this.items
    const total = list.length
    if (total === 0) {
      return { total: 0, success: 0, error: 0, avg: 0, min: 0, max: 0, p50: 0, p95: 0 }
    }
    const costs = list.map((x) => x.cost).slice().sort((a, b) => a - b)
    const sum = costs.reduce((a, b) => a + b, 0)
    const pick = (q: number) => costs[Math.min(costs.length - 1, Math.max(0, Math.floor((costs.length - 1) * q)))]
    const success = list.filter((x) => x.ok).length
    const error = total - success
    return {
      total,
      success,
      error,
      avg: Math.round(sum / total),
      min: costs[0],
      max: costs[costs.length - 1],
      p50: pick(0.5),
      p95: pick(0.95),
      last: list[list.length - 1]
    }
  }

  entries() { return this.items.slice() }
}

/** 请求日志存储（内存） */
class LogStore {
  private opt: Required<LogStoreOptions>
  private items: LogEntry[] = []
  constructor(opt?: LogStoreOptions) {
    this.opt = {
      enabled: opt?.enabled ?? false,
      maxEntries: opt?.maxEntries ?? 300
    }
  }
  setOptions(opt?: LogStoreOptions) {
    this.opt = {
      enabled: opt?.enabled ?? this.opt.enabled,
      maxEntries: opt?.maxEntries ?? this.opt.maxEntries
    }
  }
  push(it: LogEntry) {
    if (!this.opt.enabled) return
    this.items.push(it)
    if (this.items.length > this.opt.maxEntries) this.items.splice(0, this.items.length - this.opt.maxEntries)
  }
  clear() { this.items = [] }
  entries() { return this.items.slice() }
}

type PendingItem = {
  promise: Promise<any>
  controller?: CancelController
}

export class ZRequest {
  defaults: Required<ZRequestConfig>
  interceptors: {
    request: InterceptorManager<RequestInterceptor>
    response: InterceptorManager<ResponseInterceptor>
    error: InterceptorManager<ErrorInterceptor>
  }

  private pending = new Map<string, PendingItem>()
  private cache = new SimpleCache()
  private sem: PrioritySemaphore
  private metrics: MetricsCollector
  private logstore: LogStore

  constructor(config?: ZRequestConfig) {
    const d: Required<ZRequestConfig> = {
      baseURL: '',
      timeout: 15000,
      headers: {},
      token: '',
      tokenHeader: 'Authorization',
      tokenPrefix: 'Bearer ',
      showLoading: false,
      loadingTitle: '加载中…',
      loadingDelay: 150,
      dedupe: true,
      dedupeStrategy: 'reuse',
      maxConcurrent: 6,
      defaultPriority: 'normal',
      retry: 0,
      retryDelay: 300,
      cache: { enabled: false, ttl: 30000 },
      mock: { enabled: false, delay: 80, routes: [], logHit: false },
      metrics: { enabled: false, sampleRate: 1, maxEntries: 200, onRecord: (() => {}) as any },
      logStore: { enabled: false, maxEntries: 300 },
      debug: false,
      onError: undefined as any,
      dataOnly: true,
      validateStatus: defaultValidateStatus,
      logger: { enabled: false, level: 'info' }
    }

    this.defaults = deepMerge(d, config || {})

    // debug: force enable logger
    if (this.defaults.debug) {
      this.defaults.logger.enabled = true
      if (!this.defaults.logger.level) this.defaults.logger.level = 'debug'
      // also enable log store/metrics by default for debug
      this.defaults.logStore.enabled = this.defaults.logStore.enabled ?? true
      this.defaults.metrics.enabled = this.defaults.metrics.enabled ?? true
    }

    this.interceptors = {
      request: new InterceptorManager<RequestInterceptor>(),
      response: new InterceptorManager<ResponseInterceptor>(),
      error: new InterceptorManager<ErrorInterceptor>()
    }

    this.sem = new PrioritySemaphore(this.defaults.maxConcurrent)
    this.metrics = new MetricsCollector(this.defaults.metrics)
    this.logstore = new LogStore(this.defaults.logStore)
  }

  setConfig(partial: Partial<ZRequestConfig>) {
    this.defaults = deepMerge(this.defaults, partial || {})
    if (this.defaults.debug) {
      this.defaults.logger.enabled = true
      if (!this.defaults.logger.level) this.defaults.logger.level = 'debug'
    }
    this.sem.setMax(this.defaults.maxConcurrent)
    this.metrics.setOptions(this.defaults.metrics)
    this.logstore.setOptions(this.defaults.logStore)
  }

  createCancelController() {
    return new CancelController()
  }

  /** 读取性能快照 */
  metricsSnapshot() { return this.metrics.snapshot() }
  metricsEntries() { return this.metrics.entries() }
  metricsClear() { this.metrics.clear() }

  /** 读取日志 */
  logs() { return this.logstore.entries() }
  logsClear() { this.logstore.clear() }

  private log(level: 'debug'|'info'|'warn'|'error', msg: string, ctx?: Partial<RequestContext>, extra?: any) {
    const { should, print } = toLoggerPrint(this.defaults.logger)
    this.logstore.push({ time: now(), id: (ctx?.id || uid()), level, msg, ctx, extra })
    if (!should(level)) return
    if (this.defaults.debug && ctx) {
      print(level, msg, { id: ctx.id, method: ctx.method, url: ctx.fullURL, attempt: ctx.attempt, meta: ctx.meta }, extra ?? '')
    } else {
      print(level, msg, extra ?? '')
    }
  }

  private getDedupeKey(ctx: RequestContext) {
    const data = ctx.data === undefined ? '' : JSON.stringify(ctx.data)
    return `${ctx.method} ${ctx.fullURL} ${data}`
  }

  private getCacheKey(ctx: RequestContext, cacheOpt?: CacheOptions) {
    if (cacheOpt?.key) return cacheOpt.key(ctx)
    return `${ctx.method} ${ctx.fullURL}`
  }

  private shouldCache(ctx: RequestContext, cacheOpt?: CacheOptions) {
    const c = cacheOpt || this.defaults.cache
    if (!c?.enabled) return false
    if (ctx.method !== 'GET') return false
    if (!c.include) return true
    if (c.include instanceof RegExp) return c.include.test(ctx.fullURL)
    return !!c.include(ctx)
  }

  private shouldMock(opt?: RequestOptions): boolean {
    if (opt?.mock === true) return true
    if (opt?.mock === false) return false
    return !!this.defaults.mock?.enabled
  }

  private matchMockRoute(ctx: RequestContext): MockRoute | null {
    const m = this.defaults.mock
    if (!m?.enabled) return null
    const routes = m.routes || []
    for (const r of routes) {
      // method filter
      if (r.method) {
        const ms = Array.isArray(r.method) ? r.method : [r.method]
        if (!ms.includes(ctx.method)) continue
      }
      const mm = r.match
      let ok = false
      if (typeof mm === 'string') ok = ctx.url === mm || ctx.fullURL.includes(mm)
      else if (mm instanceof RegExp) ok = mm.test(ctx.url) || mm.test(ctx.fullURL)
      else if (typeof mm === 'function') ok = !!mm(ctx)
      if (ok) return r
    }
    return null
  }

  private async resolveMock<T>(ctx: RequestContext, opt: RequestOptions, controller?: CancelController): Promise<ZResponse<T> | null> {
    if (!this.shouldMock(opt)) return null
    const route = this.matchMockRoute(ctx)
    if (!route) return null

    ctx.meta.mocked = true
    const delay = route.delay ?? this.defaults.mock?.delay ?? 0
    if (this.defaults.mock?.logHit) this.log('debug', `[z-request][mock-hit] ${ctx.method} ${ctx.url}`, ctx)

    // support cancellable delay (split steps)
    const wait = async (ms: number) => {
      const step = 50
      let left = ms
      while (left > 0) {
        if (controller?.aborted) throw makeError('CANCELLED', String(controller.reason || 'cancelled'))
        await new Promise((r) => setTimeout(r, Math.min(step, left)))
        left -= step
      }
    }
    if (delay > 0) await wait(delay)

    const raw = await route.handler(ctx)
    // handler can return response-like or plain data
    if (raw && typeof raw === 'object' && ('statusCode' in raw || 'data' in raw)) {
      const statusCode = (raw.statusCode ?? 200) as number
      return {
        data: (raw.data ?? raw) as any,
        statusCode,
        header: raw.header ?? {},
        cookies: raw.cookies,
        errMsg: raw.errMsg ?? 'mock ok'
      }
    }
    return {
      data: raw as any,
      statusCode: 200,
      header: {},
      errMsg: 'mock ok'
    }
  }

  async request<T = any>(url: string, method: HttpMethod, data?: any, options?: RequestOptions): Promise<T> {
    const id = uid()
    const mergedOpt: RequestOptions = options || {}
    const timeout = mergedOpt.timeout ?? this.defaults.timeout
    const params = mergedOpt.params
    const fullURL = buildFullURL(this.defaults.baseURL, url, params)

    const header = deepMerge({}, this.defaults.headers, mergedOpt.header || {})
    const showLoading = mergedOpt.showLoading ?? this.defaults.showLoading

    const ctx: RequestContext = {
      id,
      url,
      fullURL,
      method,
      data,
      header,
      timeout,
      params,
      attempt: 0,
      startTime: now(),
      showLoading,
      meta: {}
    }

    // inject token
    await this.applyToken(ctx)

    // request interceptors
    let ctx2 = ctx
    const reqChain: Array<{ fulfilled: RequestInterceptor; rejected?: any }> = []
    this.interceptors.request.forEach((h) => reqChain.push(h))
    for (const h of reqChain) {
      try { ctx2 = await h.fulfilled(ctx2) } catch (e) {
        if (h.rejected) { ctx2 = await h.rejected(e) } else { throw e }
      }
    }

    const dedupe = mergedOpt.dedupe ?? this.defaults.dedupe
    const dedupeStrategy = mergedOpt.dedupeStrategy ?? this.defaults.dedupeStrategy
    const dedupeKey = this.getDedupeKey(ctx2)

    if (dedupe) {
      const existed = this.pending.get(dedupeKey)
      if (existed) {
        if (dedupeStrategy === 'reuse') return existed.promise
        if (dedupeStrategy === 'reject') throw makeError('REQUEST_FAIL', 'duplicate request', { cause: { dedupeKey } })
        if (dedupeStrategy === 'cancel-prev') {
          existed.controller?.abort('cancel previous')
          this.pending.delete(dedupeKey)
        }
      }
    }

    // cache (pre-check)
    const cacheOpt = deepMerge({}, this.defaults.cache, mergedOpt.cache || {})
    if (this.shouldCache(ctx2, cacheOpt)) {
      const ckey = this.getCacheKey(ctx2, cacheOpt)
      const cached = this.cache.get(ckey)
      if (cached !== undefined) {
        ctx2.meta.fromCache = true
        this.log('debug', `[z-request] cache hit ${ckey}`, ctx2)
        // metrics/log cache hit
        this.metrics.record({
          id: ctx2.id,
          method: ctx2.method,
          url: ctx2.url,
          fullURL: ctx2.fullURL,
          statusCode: 200,
          ok: true,
          cost: 0,
          attempt: 0,
          startTime: now(),
          endTime: now(),
          fromCache: true,
          mocked: false
        })
        return cached
      }
    }

    const controller = mergedOpt.cancelController
    const promise = this.runWithRetry<T>(ctx2, mergedOpt, controller, cacheOpt)

    if (dedupe) this.pending.set(dedupeKey, { promise, controller })

    try {
      const dataRes = await promise
      return dataRes
    } finally {
      if (dedupe) this.pending.delete(dedupeKey)
    }
  }

  private async applyToken(ctx: RequestContext) {
    const token = this.defaults.token
    let tk = ''
    try {
      if (typeof token === 'function') tk = await token() as any
      else tk = token || ''
    } catch (_) { tk = '' }

    if (tk) {
      const headerName = this.defaults.tokenHeader || 'Authorization'
      const prefix = this.defaults.tokenPrefix ?? ''
      ctx.header[headerName] = `${prefix}${tk}`
    }
  }

  private async runWithRetry<T>(
    baseCtx: RequestContext,
    opt: RequestOptions,
    controller?: CancelController,
    cacheOpt?: CacheOptions
  ): Promise<T> {
    const retry = opt.retry ?? this.defaults.retry
    const retryDelay = opt.retryDelay ?? this.defaults.retryDelay
    let attempt = 0

    while (true) {
      const ctx = { ...baseCtx, attempt, startTime: now() }
      try {
        const res = await this.runOnce<T>(ctx, opt, controller, cacheOpt)
        return res
      } catch (err: any) {
        const zerr = this.normalizeError(err, ctx)
        const cost = now() - ctx.startTime

        // record metrics/log for this attempt error
        this.metrics.record({
          id: ctx.id,
          method: ctx.method,
          url: ctx.url,
          fullURL: ctx.fullURL,
          statusCode: zerr.statusCode,
          ok: false,
          cost,
          attempt: ctx.attempt,
          startTime: ctx.startTime,
          endTime: now(),
          fromCache: false,
          mocked: !!ctx.meta.mocked,
          errorCode: zerr.code
        })
        this.log('warn', `[z-request] error ${zerr.code} ${ctx.method} ${ctx.fullURL} ${cost}ms`, ctx, zerr)

        // error interceptors
        const errChain: Array<{ fulfilled: ErrorInterceptor; rejected?: any }> = []
        this.interceptors.error.forEach((h) => errChain.push(h))
        for (const h of errChain) {
          try { await h.fulfilled(zerr, ctx) } catch (_) {}
        }

        if (controller?.aborted) throw makeError('CANCELLED', String(controller.reason || 'cancelled'), { cause: zerr })
        if (zerr.code === 'CANCELLED') throw zerr

        if (attempt < (retry || 0)) {
          const wait = typeof retryDelay === 'function' ? retryDelay(attempt + 1, zerr, ctx) : (retryDelay as number)
          this.log('warn', `[z-request] retry ${attempt + 1} wait ${wait}ms`, ctx)
          await new Promise((r) => setTimeout(r, Math.max(0, wait || 0)))
          attempt++
          continue
        }

        if (this.defaults.onError) {
          const out = this.defaults.onError(zerr, ctx)
          throw out ?? zerr
        }
        throw zerr
      }
    }
  }

  private async runOnce<T>(
    ctx: RequestContext,
    opt: RequestOptions,
    controller?: CancelController,
    cacheOpt?: CacheOptions
  ): Promise<T> {
    if (controller?.aborted) throw makeError('CANCELLED', String(controller.reason || 'cancelled'))

    // acquire with priority
    const pri = priorityToNumber(opt.priority ?? this.defaults.defaultPriority)
    await this.sem.acquire(pri)

    let loadingTimer: any = null
    try {
      // loading delay
      if (ctx.showLoading) {
        const delay = this.defaults.loadingDelay || 0
        loadingTimer = setTimeout(() => {
          try { uni.showLoading({ title: this.defaults.loadingTitle, mask: true }) } catch (_) {}
        }, Math.max(0, delay))
      }

      // mock
      const mocked = await this.resolveMock<T>(ctx, opt, controller)
      if (mocked) {
        const cost = now() - ctx.startTime
        this.log('info', `[z-request][mock] ${ctx.method} ${ctx.fullURL} ${mocked.statusCode} ${cost}ms`, ctx)

        const ok = (this.defaults.validateStatus || defaultValidateStatus)(mocked.statusCode)
        if (!ok) throw makeError('HTTP', `HTTP ${mocked.statusCode}`, { statusCode: mocked.statusCode, response: mocked })

        // response interceptors
        let out: any = mocked
        const resChain: Array<{ fulfilled: ResponseInterceptor; rejected?: any }> = []
        this.interceptors.response.forEach((h) => resChain.push(h))
        for (const h of resChain) out = await h.fulfilled(out, ctx)

        const dataOnly = opt.dataOnly ?? this.defaults.dataOnly
        const finalData = dataOnly ? (out?.data ?? out) : out

        // cache set
        if (this.shouldCache(ctx, cacheOpt)) {
          const ttl = cacheOpt?.ttl ?? this.defaults.cache?.ttl ?? 0
          const ckey = this.getCacheKey(ctx, cacheOpt)
          this.cache.set(ckey, finalData, ttl || 0)
        }

        this.metrics.record({
          id: ctx.id,
          method: ctx.method,
          url: ctx.url,
          fullURL: ctx.fullURL,
          statusCode: mocked.statusCode,
          ok: true,
          cost,
          attempt: ctx.attempt,
          startTime: ctx.startTime,
          endTime: now(),
          fromCache: false,
          mocked: true
        })

        return finalData as T
      }

      // real network
      const res: ZResponse = await new Promise((resolve, reject) => {
        const task = uni.request({
          url: ctx.fullURL,
          method: ctx.method as any,
          data: ctx.data,
          header: ctx.header,
          timeout: ctx.timeout,
          success: (r) => resolve(r as any),
          fail: (e) => reject(e),
        })
        if (controller) controller._bind(task)
      })

      const cost = now() - ctx.startTime
      this.log('info', `[z-request] ${ctx.method} ${ctx.fullURL} ${res.statusCode} ${cost}ms`, ctx)

      // validate status
      const ok = (this.defaults.validateStatus || defaultValidateStatus)(res.statusCode)
      if (!ok) {
        throw makeError('HTTP', `HTTP ${res.statusCode}`, { statusCode: res.statusCode, response: res })
      }

      // response interceptors
      let out: any = res
      const resChain: Array<{ fulfilled: ResponseInterceptor; rejected?: any }> = []
      this.interceptors.response.forEach((h) => resChain.push(h))
      for (const h of resChain) out = await h.fulfilled(out, ctx)

      const dataOnly = opt.dataOnly ?? this.defaults.dataOnly
      const finalData = dataOnly ? (out?.data ?? out) : out

      // cache set
      if (this.shouldCache(ctx, cacheOpt)) {
        const ttl = cacheOpt?.ttl ?? this.defaults.cache?.ttl ?? 0
        const ckey = this.getCacheKey(ctx, cacheOpt)
        this.cache.set(ckey, finalData, ttl || 0)
      }

      // metrics record
      this.metrics.record({
        id: ctx.id,
        method: ctx.method,
        url: ctx.url,
        fullURL: ctx.fullURL,
        statusCode: res.statusCode,
        ok: true,
        cost,
        attempt: ctx.attempt,
        startTime: ctx.startTime,
        endTime: now(),
        fromCache: false,
        mocked: false
      })

      return finalData as T
    } finally {
      if (loadingTimer) clearTimeout(loadingTimer)
      if (ctx.showLoading) {
        try { uni.hideLoading() } catch (_) {}
      }
      this.sem.release()
    }
  }

  private normalizeError(err: any, ctx: RequestContext): ZRequestError {
    if (err?.isZRequestError) return err as ZRequestError
    const msg = err?.errMsg || err?.message || 'request failed'
    // uni.request: timeout -> errMsg includes 'timeout'
    if (typeof msg === 'string' && msg.toLowerCase().includes('timeout')) {
      return makeError('TIMEOUT', msg, { cause: err })
    }
    if (ctx && (err?.statusCode || err?.response?.statusCode)) {
      return makeError('HTTP', msg, { statusCode: err.statusCode || err.response?.statusCode, response: err.response, cause: err })
    }
    if (typeof msg === 'string' && msg.toLowerCase().includes('abort')) {
      return makeError('CANCELLED', msg, { cause: err })
    }
    return makeError('NETWORK', msg, { cause: err })
  }

  // shorthand
  get<T = any>(url: string, params?: ZAnyObj, options?: RequestOptions) {
    return this.request<T>(url, 'GET', undefined, { ...(options || {}), params })
  }
  post<T = any>(url: string, data?: any, options?: RequestOptions) {
    return this.request<T>(url, 'POST', data, options)
  }
  put<T = any>(url: string, data?: any, options?: RequestOptions) {
    return this.request<T>(url, 'PUT', data, options)
  }
  del<T = any>(url: string, data?: any, options?: RequestOptions) {
    return this.request<T>(url, 'DELETE', data, options)
  }

  /** 上传 */
  upload<T = any>(
    url: string,
    payload: { filePath: string; name?: string; formData?: ZAnyObj; header?: Record<string,string> },
    options?: { onProgress?: (p: UniApp.UploadProgressUpdateCallbackResult) => void; cancelController?: CancelController; mock?: boolean; priority?: Priority }
  ) {
    const fullURL = joinURL(this.defaults.baseURL || '', url)
    const header = deepMerge({}, this.defaults.headers, payload.header || {})
    const controller = options?.cancelController

    return new Promise<T>(async (resolve, reject) => {
      const ctx: RequestContext = {
        id: uid(),
        url,
        fullURL,
        method: 'POST',
        data: payload.formData,
        header,
        timeout: this.defaults.timeout,
        params: undefined,
        attempt: 0,
        startTime: now(),
        showLoading: false,
        meta: { upload: true }
      }
      await this.applyToken(ctx)

      // queue + priority
      const pri = priorityToNumber(options?.priority ?? this.defaults.defaultPriority)
      await this.sem.acquire(pri)

      try {
        // mock
        const opt: RequestOptions = { mock: options?.mock }
        const mocked = await this.resolveMock<T>(ctx, opt, controller)
        if (mocked) {
          // simulate progress
          if (options?.onProgress) {
            let p = 0
            const timer = setInterval(() => {
              p = Math.min(100, p + 12)
              try { options.onProgress({ progress: p, totalBytesSent: p, totalBytesExpectedToSend: 100 } as any) } catch (_) {}
              if (p >= 100) clearInterval(timer)
            }, 120)
          }
          resolve((mocked.data as any) as T)
          return
        }

        const task = uni.uploadFile({
          url: ctx.fullURL,
          filePath: payload.filePath,
          name: payload.name || 'file',
          formData: payload.formData || {},
          header: ctx.header,
          success: (r) => {
            let data: any = r.data
            try { data = JSON.parse(r.data as any) } catch (_) {}
            resolve(data as T)
          },
          fail: (e) => reject(this.normalizeError(e, ctx))
        })
        if (controller) controller._bind(task as any)
        if (options?.onProgress && (task as any).onProgressUpdate) (task as any).onProgressUpdate(options.onProgress)
      } finally {
        this.sem.release()
      }
    })
  }

  /** 下载（返回临时文件路径 / mock 返回 mock://...） */
  download(
    url: string,
    options?: { header?: Record<string,string>; cancelController?: CancelController; onProgress?: (p: any) => void; mock?: boolean; priority?: Priority }
  ) {
    const fullURL = joinURL(this.defaults.baseURL || '', url)
    const header = deepMerge({}, this.defaults.headers, options?.header || {})
    const controller = options?.cancelController

    return new Promise<string>(async (resolve, reject) => {
      const ctx: RequestContext = {
        id: uid(),
        url,
        fullURL,
        method: 'GET',
        data: undefined,
        header,
        timeout: this.defaults.timeout,
        params: undefined,
        attempt: 0,
        startTime: now(),
        showLoading: false,
        meta: { download: true }
      }
      await this.applyToken(ctx)

      // queue + priority
      const pri = priorityToNumber(options?.priority ?? this.defaults.defaultPriority)
      await this.sem.acquire(pri)

      try {
        // mock
        const opt: RequestOptions = { mock: options?.mock }
        const mocked = await this.resolveMock<any>(ctx, opt, controller)
        if (mocked) {
          // simulate progress + return fake path
          if (options?.onProgress) {
            let p = 0
            const timer = setInterval(() => {
              p = Math.min(100, p + 10)
              try { options.onProgress({ progress: p, totalBytesWritten: p, totalBytesExpectedToWrite: 100 } as any) } catch (_) {}
              if (p >= 100) clearInterval(timer)
            }, 100)
          }
          resolve(`mock://download/${Date.now()}.bin`)
          return
        }

        const task: any = uni.downloadFile({
          url: ctx.fullURL,
          header: ctx.header,
          success: (r) => {
            if (r.statusCode && r.statusCode >= 200 && r.statusCode < 300) resolve((r as any).tempFilePath)
            else reject(makeError('HTTP', `HTTP ${r.statusCode}`, { statusCode: r.statusCode as any }))
          },
          fail: (e) => reject(this.normalizeError(e, ctx))
        })
        if (controller) controller._bind(task as any)
        if (options?.onProgress && task?.onProgressUpdate) task.onProgressUpdate(options.onProgress)
      } finally {
        this.sem.release()
      }
    })
  }

  /** 清缓存 */
  cacheClear() { this.cache.clear() }
  cacheDelete(key: string) { this.cache.delete(key) }
}

export function createZRequest(config?: ZRequestConfig) {
  return new ZRequest(config)
}

export const ZRequestPlugin = {
  install(app: any, config?: ZRequestConfig) {
    const ins = createZRequest(config)
    app.config.globalProperties.$zRequest = ins
    app.provide('zRequest', ins)
  }
}

/** setup 注入 */
export function useZRequest(): ZRequest {
  const ins = inject<ZRequest>('zRequest' as any, null as any)
  if (ins) return ins
  const vm = getCurrentInstance()
  const gp = vm?.appContext?.config?.globalProperties as any
  if (gp?.$zRequest) return gp.$zRequest
  // 给出更友好的错误，避免出现 “Cannot read properties of undefined (reading 'get')”
  throw new Error('[z-request] 未安装：请在 main.ts/main.js 里执行 app.use(ZRequestPlugin, config)')
}
