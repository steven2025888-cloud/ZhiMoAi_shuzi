// zhimo-ui datetime helpers (Vue3 / uni-app)
// Keep small, dependency-free, and easy to read.

export type DateLike = string | number | Date | null | undefined

export function pad2(n: number): string {
  return n < 10 ? `0${n}` : `${n}`
}

export function isValidDate(d: Date): boolean {
  return d instanceof Date && !Number.isNaN(d.getTime())
}

export function toDate(input: DateLike): Date | null {
  if (input == null) return null
  if (input instanceof Date) return isValidDate(input) ? input : null
  if (typeof input === 'number') {
    const d = new Date(input)
    return isValidDate(d) ? d : null
  }
  if (typeof input === 'string') {
    const s = input.trim()
    if (!s) return null
    // Support: YYYY-MM, YYYY-MM-DD, YYYY-MM-DD HH:mm, HH:mm(:ss)
    const m = s.match(/^(\d{4})-(\d{2})(?:-(\d{2}))?(?:\s+(\d{2}):(\d{2})(?::(\d{2}))?)?$/)
    if (m) {
      const y = Number(m[1])
      const mo = Number(m[2]) - 1
      const da = m[3] ? Number(m[3]) : 1
      const hh = m[4] ? Number(m[4]) : 0
      const mm = m[5] ? Number(m[5]) : 0
      const ss = m[6] ? Number(m[6]) : 0
      const d = new Date(y, mo, da, hh, mm, ss)
      return isValidDate(d) ? d : null
    }
    const t = s.match(/^(\d{2}):(\d{2})(?::(\d{2}))?$/)
    if (t) {
      const hh = Number(t[1])
      const mm = Number(t[2])
      const ss = t[3] ? Number(t[3]) : 0
      const d = new Date()
      d.setHours(hh, mm, ss, 0)
      return isValidDate(d) ? d : null
    }
  }
  return null
}

export function clampDate(d: Date, min?: DateLike, max?: DateLike): Date {
  const minD = toDate(min)
  const maxD = toDate(max)
  let t = d.getTime()
  if (minD) t = Math.max(t, minD.getTime())
  if (maxD) t = Math.min(t, maxD.getTime())
  return new Date(t)
}

export function daysInMonth(y: number, m1to12: number): number {
  return new Date(y, m1to12, 0).getDate()
}

export function formatDate(d: Date, fmt: 'ym' | 'ymd' | 'ymdh' | 'ymdhm' | 'time' | 'times' = 'ymd'): string {
  const y = d.getFullYear()
  const mo = pad2(d.getMonth() + 1)
  const da = pad2(d.getDate())
  const hh = pad2(d.getHours())
  const mm = pad2(d.getMinutes())
  const ss = pad2(d.getSeconds())
  switch (fmt) {
    case 'ym':
      return `${y}-${mo}`
    case 'ymd':
      return `${y}-${mo}-${da}`
    case 'ymdh':
      return `${y}-${mo}-${da} ${hh}`
    case 'ymdhm':
      return `${y}-${mo}-${da} ${hh}:${mm}`
    case 'time':
      return `${hh}:${mm}`
    case 'times':
      return `${hh}:${mm}:${ss}`
    default:
      return `${y}-${mo}-${da}`
  }
}

export function diffDays(a: Date, b: Date): number {
  const t1 = new Date(a.getFullYear(), a.getMonth(), a.getDate()).getTime()
  const t2 = new Date(b.getFullYear(), b.getMonth(), b.getDate()).getTime()
  return Math.floor((t2 - t1) / 86400000)
}

export function addDays(d: Date, delta: number): Date {
  const x = new Date(d.getTime())
  x.setDate(x.getDate() + delta)
  return x
}

export function sameYmd(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}
