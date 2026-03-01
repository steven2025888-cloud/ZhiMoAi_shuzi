declare const zUtils: {
  // types
  isNil(v: any): boolean
  isDef(v: any): boolean
  isString(v: any): boolean
  isNumber(v: any): boolean
  isBoolean(v: any): boolean
  isFunction(v: any): boolean
  isArray(v: any): boolean
  isDate(v: any): boolean
  isObject(v: any): boolean
  isPlainObject(v: any): boolean
  isPromise(v: any): boolean

  // number
  clamp(n: any, min: number, max: number): number
  toNumber(v: any, fallback?: number): number
  toInt(v: any, fallback?: number): number
  round(n: any, digits?: number): number
  padZero(v: any, len?: number): string
  randomInt(min?: number, max?: number): number
  randomFloat(min?: number, max?: number, digits?: number): number
  formatThousands(n: any, sep?: string, digits?: number): string
  formatCurrency(n: any, opts?: { symbol?: string; digits?: number; thousandSep?: string; decimalSep?: string }): string
  parseCurrency(text: any): number

  // string
  trim(s: any): string
  trimAll(s: any): string
  capitalize(s: any): string
  lowerFirst(s: any): string
  camelize(s: any): string
  kebabize(s: any): string
  snakeize(s: any): string
  truncate(s: any, max?: number, suffix?: string): string
  maskPhoneCN(phone: any): string
  maskEmail(email: any): string
  escapeHtml(s: any): string
  unescapeHtml(s: any): string
  bytesLength(s: any): number

  // array
  unique<T>(arr: T[]): T[]
  uniqueBy<T>(arr: T[], keyFn: (x: T) => any): T[]
  chunk<T>(arr: T[], size?: number): T[][]
  flatten<T>(arr: any[], depth?: number): any[]
  groupBy<T>(arr: T[], key: ((x: T) => any) | string): Record<string, T[]>
  sortBy<T>(arr: T[], key: ((x: T) => any) | string, order?: 'asc' | 'desc'): T[]
  shuffle<T>(arr: T[]): T[]
  sample<T>(arr: T[]): T | undefined
  range(start: number, end: number, step?: number): number[]
  sum(arr: any[]): number
  sumBy<T>(arr: T[], key: ((x: T) => any) | string): number

  // object
  pick<T extends Record<string, any>>(obj: T, keys: string[]): Partial<T>
  omit<T extends Record<string, any>>(obj: T, keys: string[]): Partial<T>
  get(obj: any, path: string | string[], fallback?: any): any
  set(obj: any, path: string | string[], value: any): any
  deepClone<T>(val: T): T
  deepMerge<T extends Record<string, any>>(target: T, ...sources: any[]): T
  isEqual(a: any, b: any): boolean

  // date
  now(): number
  parseDate(input: any): Date | null
  formatDate(date: any, fmt?: string): string
  addDays(date: any, days?: number): Date
  startOfDay(date: any): Date
  endOfDay(date: any): Date
  startOfWeek(date: any, weekStartsOn?: number): Date
  startOfMonth(date: any): Date
  diffMs(a: any, b: any): number
  fromNow(date: any, opts?: { justNowSec?: number; suffix?: string; fixedDay?: boolean }): string

  // function control
  debounce<T extends (...args: any[]) => any>(fn: T, wait?: number, opts?: { leading?: boolean; trailing?: boolean }): T
  throttle<T extends (...args: any[]) => any>(fn: T, wait?: number, opts?: { leading?: boolean; trailing?: boolean }): T
  once<T extends (...args: any[]) => any>(fn: T): T

  // url
  parseQuery(query: any): Record<string, any>
  stringifyQuery(obj: any): string
  joinUrl(baseUrl: any, path: any, query?: any): string

  // validate
  isEmail(v: any): boolean
  isPhoneCN(v: any): boolean
  isUrl(v: any): boolean
  isBankCard(v: any): boolean
  isHexColor(v: any): boolean

  // color
  hexToRgb(hex: any): { r: number; g: number; b: number } | null
  rgbToHex(r: any, g: any, b: any): string
  randomHexColor(): string
  lighten(hex: any, amount?: number): string
  darken(hex: any, amount?: number): string
  mixColor(hexA: any, hexB: any, weight?: number): string | null

  // storage
  setStorage(key: any, value: any, opts?: { expireMs?: number }): boolean
  getStorage<T = any>(key: any, fallback?: T): T
  removeStorage(key: any): boolean
  clearStorage(): boolean

  // platform
  getSystemInfo(): Record<string, any>
  getPlatform(): string
  isH5(): boolean
  isIOS(): boolean
  isAndroid(): boolean

  // clipboard
  copyText(text: any): Promise<boolean>

  // base64 / file
  readFileAsBase64(filePath: any): Promise<string>
  saveBase64ToTempFile(base64: any, opts?: { ext?: string; prefix?: string }): Promise<string>

  // ui
  toast(title: any, opts?: { icon?: 'none' | 'success' | 'error' | 'loading'; duration?: number }): void
  loading(title?: any, opts?: { mask?: boolean }): void
  hideLoading(): void
}

export default zUtils
export { zUtils }
