/**
 * Lightweight form validation helpers (Vue3 / uni-app).
 * Keep rules simple and explicit to reduce runtime edge cases.
 */

export function isEmpty(val) {
  return val === undefined || val === null || (typeof val === 'string' && val.trim() === '') ||
    (Array.isArray(val) && val.length === 0)
}

export async function runRule(rule, value, ctx = {}) {
  // rule: { required, message, min, max, pattern, validator }
  if (!rule) return null

  const msg = rule.message || 'Invalid value'

  if (rule.required && isEmpty(value)) return msg

  if (typeof rule.min === 'number') {
    const len = (typeof value === 'string' || Array.isArray(value)) ? value.length : Number(value)
    if (len < rule.min) return msg
  }
  if (typeof rule.max === 'number') {
    const len = (typeof value === 'string' || Array.isArray(value)) ? value.length : Number(value)
    if (len > rule.max) return msg
  }

  if (rule.pattern instanceof RegExp) {
    if (typeof value !== 'string' || !rule.pattern.test(value)) return msg
  }

  if (typeof rule.validator === 'function') {
    try {
      const res = await rule.validator(value, ctx)
      if (res === false) return msg
      if (typeof res === 'string' && res) return res
    } catch (e) {
      return (e && e.message) ? e.message : msg
    }
  }

  return null
}

export async function validateValue(rules, value, ctx = {}) {
  if (!rules || rules.length === 0) return null
  for (const rule of rules) {
    const err = await runRule(rule, value, ctx)
    if (err) return err
  }
  return null
}
