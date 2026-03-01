/**
 * Zhimo-UI | z-utils
 * A zero-dependency utility toolkit for uni-app (Vue 3).
 * Rewritten from scratch (no third‑party code copy) to avoid infringement.
 *
 * Usage:
 *   import zUtils from '@/uni_modules/zhimo-ui/js_sdk/z-utils'
 *   zUtils.formatDate(new Date(), 'yyyy-MM-dd HH:mm:ss')
 */

const _toString = Object.prototype.toString;
const _hasOwn = Object.prototype.hasOwnProperty;

function isNil(v) { return v === null || v === undefined; }
function isDef(v) { return v !== null && v !== undefined; }
function isString(v) { return typeof v === 'string' || v instanceof String; }
function isNumber(v) { return typeof v === 'number' && !Number.isNaN(v); }
function isBoolean(v) { return typeof v === 'boolean'; }
function isFunction(v) { return typeof v === 'function'; }
function isArray(v) { return Array.isArray(v); }
function isDate(v) { return _toString.call(v) === '[object Date]'; }
function isObject(v) { return v !== null && typeof v === 'object'; }
function isPlainObject(v) {
  if (!isObject(v)) return false;
  const proto = Object.getPrototypeOf(v);
  return proto === Object.prototype || proto === null;
}
function isPromise(v) { return isObject(v) && isFunction(v.then) && isFunction(v.catch); }

function clamp(n, min, max) {
  const x = Number(n);
  if (Number.isNaN(x)) return min;
  return Math.min(max, Math.max(min, x));
}
function toNumber(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}
function toInt(v, fallback = 0) { return Math.trunc(toNumber(v, fallback)); }
function round(n, digits = 0) {
  const x = toNumber(n, 0);
  const p = 10 ** clamp(digits, 0, 12);
  return Math.round(x * p) / p;
}
function padZero(v, len = 2) {
  const s = String(v ?? '');
  if (s.length >= len) return s;
  return '0'.repeat(len - s.length) + s;
}
function randomInt(min = 0, max = 100) {
  const a = Math.ceil(Math.min(min, max));
  const b = Math.floor(Math.max(min, max));
  return Math.floor(Math.random() * (b - a + 1)) + a;
}
function randomFloat(min = 0, max = 1, digits = 4) {
  const a = Math.min(min, max);
  const b = Math.max(min, max);
  return round(a + Math.random() * (b - a), digits);
}
function formatThousands(n, sep = ',', digits) {
  const x = toNumber(n, NaN);
  if (!Number.isFinite(x)) return String(n ?? '');
  const fixed = isDef(digits) ? round(x, digits).toFixed(digits) : String(x);
  const parts = fixed.split('.');
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, sep);
  return parts.join('.');
}
function formatCurrency(n, { symbol = '¥', digits = 2, thousandSep = ',', decimalSep = '.' } = {}) {
  const x = toNumber(n, NaN);
  if (!Number.isFinite(x)) return String(n ?? '');
  const sign = x < 0 ? '-' : '';
  const abs = Math.abs(x);
  const fixed = abs.toFixed(clamp(digits, 0, 8));
  let [i, d] = fixed.split('.');
  i = i.replace(/\B(?=(\d{3})+(?!\d))/g, thousandSep);
  return sign + symbol + i + (digits ? (decimalSep + d) : '');
}
function parseCurrency(text) {
  if (text == null) return NaN;
  const s = String(text).replace(/[^\d.\-]/g, '');
  const n = Number(s);
  return Number.isFinite(n) ? n : NaN;
}

// strings
function trim(s) { return String(s ?? '').replace(/^\s+|\s+$/g, ''); }
function trimAll(s) { return String(s ?? '').replace(/\s+/g, ''); }
function capitalize(s) {
  const str = String(s ?? '');
  return str.length ? (str[0].toLocaleUpperCase() + str.slice(1)) : str;
}
function lowerFirst(s) {
  const str = String(s ?? '');
  return str.length ? (str[0].toLocaleLowerCase() + str.slice(1)) : str;
}
function camelize(s) {
  return String(s ?? '').trim().replace(/[-_\s]+(.)?/g, (_, c) => (c ? c.toUpperCase() : '')).replace(/^(.)/, (m) => m.toLowerCase());
}
function kebabize(s) {
  return String(s ?? '').replace(/([a-z0-9])([A-Z])/g, '$1-$2').replace(/[\s_]+/g, '-').toLowerCase();
}
function snakeize(s) {
  return String(s ?? '').replace(/([a-z0-9])([A-Z])/g, '$1_$2').replace(/[\s-]+/g, '_').toLowerCase();
}
function truncate(s, max = 20, suffix = '…') {
  const str = String(s ?? '');
  if (str.length <= max) return str;
  return str.slice(0, Math.max(0, max - suffix.length)) + suffix;
}
function maskPhoneCN(phone) {
  const s = String(phone ?? '');
  return /^\d{11}$/.test(s) ? s.replace(/^(\d{3})\d{4}(\d{4})$/, '$1****$2') : s;
}
function maskEmail(email) {
  const s = String(email ?? '');
  const m = s.match(/^([^@]+)@(.+)$/);
  if (!m) return s;
  const name = m[1];
  const host = m[2];
  const shown = name.length <= 2 ? name[0] + '*' : name[0] + '*'.repeat(Math.min(6, name.length - 2)) + name[name.length - 1];
  return `${shown}@${host}`;
}
function escapeHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
function unescapeHtml(s) {
  return String(s ?? '')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, '&');
}
function bytesLength(s) {
  // UTF-8 byte length (approx, without TextEncoder fallback)
  const str = String(s ?? '');
  if (typeof TextEncoder !== 'undefined') return new TextEncoder().encode(str).length;
  let bytes = 0;
  for (let i = 0; i < str.length; i++) {
    const code = str.charCodeAt(i);
    if (code <= 0x7f) bytes += 1;
    else if (code <= 0x7ff) bytes += 2;
    else if (code >= 0xd800 && code <= 0xdbff) { bytes += 4; i++; } // surrogate pair
    else bytes += 3;
  }
  return bytes;
}

// arrays
function unique(arr) {
  if (!isArray(arr)) return [];
  return Array.from(new Set(arr));
}
function uniqueBy(arr, keyFn) {
  if (!isArray(arr)) return [];
  const fn = isFunction(keyFn) ? keyFn : (v) => v;
  const seen = new Set();
  const out = [];
  for (const it of arr) {
    const k = fn(it);
    if (!seen.has(k)) { seen.add(k); out.push(it); }
  }
  return out;
}
function chunk(arr, size = 2) {
  const a = isArray(arr) ? arr : [];
  const s = Math.max(1, toInt(size, 2));
  const out = [];
  for (let i = 0; i < a.length; i += s) out.push(a.slice(i, i + s));
  return out;
}
function flatten(arr, depth = 1) {
  const a = isArray(arr) ? arr : [];
  const d = Math.max(0, toInt(depth, 1));
  return d === 0 ? a.slice() : a.reduce((acc, v) => acc.concat(isArray(v) ? flatten(v, d - 1) : v), []);
}
function groupBy(arr, key) {
  const a = isArray(arr) ? arr : [];
  const fn = isFunction(key) ? key : (v) => (isObject(v) ? v[key] : undefined);
  return a.reduce((m, v) => {
    const k = String(fn(v));
    (m[k] ||= []).push(v);
    return m;
  }, {});
}
function sortBy(arr, key, order = 'asc') {
  const a = (isArray(arr) ? arr.slice() : []);
  const fn = isFunction(key) ? key : (v) => (isObject(v) ? v[key] : v);
  const dir = order === 'desc' ? -1 : 1;
  a.sort((x, y) => {
    const ax = fn(x); const ay = fn(y);
    if (ax === ay) return 0;
    return (ax > ay ? 1 : -1) * dir;
  });
  return a;
}
function shuffle(arr) {
  const a = isArray(arr) ? arr.slice() : [];
  for (let i = a.length - 1; i > 0; i--) {
    const j = randomInt(0, i);
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}
function sample(arr) {
  const a = isArray(arr) ? arr : [];
  return a.length ? a[randomInt(0, a.length - 1)] : undefined;
}
function range(start, end, step = 1) {
  const s = toInt(start, 0);
  const e = toInt(end, 0);
  const st = Math.max(1, Math.abs(toInt(step, 1))) * (e >= s ? 1 : -1);
  const out = [];
  for (let i = s; (st > 0 ? i <= e : i >= e); i += st) out.push(i);
  return out;
}
function sum(arr) {
  return (isArray(arr) ? arr : []).reduce((a, b) => a + toNumber(b, 0), 0);
}
function sumBy(arr, key) {
  const fn = isFunction(key) ? key : (v) => (isObject(v) ? v[key] : v);
  return (isArray(arr) ? arr : []).reduce((a, b) => a + toNumber(fn(b), 0), 0);
}

// objects
function pick(obj, keys) {
  const o = isObject(obj) ? obj : {};
  const ks = isArray(keys) ? keys : [];
  const out = {};
  for (const k of ks) if (_hasOwn.call(o, k)) out[k] = o[k];
  return out;
}
function omit(obj, keys) {
  const o = isObject(obj) ? obj : {};
  const ks = new Set(isArray(keys) ? keys : []);
  const out = {};
  for (const k in o) if (_hasOwn.call(o, k) && !ks.has(k)) out[k] = o[k];
  return out;
}
function get(obj, path, fallback) {
  const p = isArray(path) ? path : String(path ?? '').split('.').filter(Boolean);
  let cur = obj;
  for (const k of p) {
    if (!isObject(cur) && !isArray(cur)) return fallback;
    cur = cur[k];
    if (cur === undefined) return fallback;
  }
  return cur;
}
function set(obj, path, value) {
  const p = isArray(path) ? path : String(path ?? '').split('.').filter(Boolean);
  if (!p.length) return obj;
  let cur = obj;
  for (let i = 0; i < p.length - 1; i++) {
    const k = p[i];
    if (!isObject(cur[k]) && !isArray(cur[k])) cur[k] = {};
    cur = cur[k];
  }
  cur[p[p.length - 1]] = value;
  return obj;
}
function deepClone(val) {
  // Prefer structuredClone if available
  if (typeof structuredClone === 'function') {
    try { return structuredClone(val); } catch (_) {}
  }
  if (!isObject(val)) return val;
  if (isDate(val)) return new Date(val.getTime());
  if (isArray(val)) return val.map(deepClone);
  const out = {};
  for (const k in val) if (_hasOwn.call(val, k)) out[k] = deepClone(val[k]);
  return out;
}
function deepMerge(target, ...sources) {
  const t = isPlainObject(target) ? target : {};
  for (const src of sources) {
    if (!isPlainObject(src)) continue;
    for (const k in src) {
      if (!_hasOwn.call(src, k)) continue;
      const v = src[k];
      if (isPlainObject(v) && isPlainObject(t[k])) t[k] = deepMerge(t[k], v);
      else t[k] = deepClone(v);
    }
  }
  return t;
}
function isEqual(a, b) {
  if (a === b) return true;
  if (Number.isNaN(a) && Number.isNaN(b)) return true;
  if (isDate(a) && isDate(b)) return a.getTime() === b.getTime();
  if (isArray(a) && isArray(b)) {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) if (!isEqual(a[i], b[i])) return false;
    return true;
  }
  if (isPlainObject(a) && isPlainObject(b)) {
    const ka = Object.keys(a); const kb = Object.keys(b);
    if (ka.length !== kb.length) return false;
    for (const k of ka) if (!isEqual(a[k], b[k])) return false;
    return true;
  }
  return false;
}

// time & date
function now() { return Date.now(); }
function parseDate(input) {
  if (isDate(input)) return new Date(input.getTime());
  if (isNumber(input)) return new Date(input);
  if (isString(input)) {
    // Accept "YYYY-MM-DD HH:mm:ss" and ISO-ish
    const s = String(input).trim().replace(/T/, ' ').replace(/-/g, '/');
    const d = new Date(s);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  return null;
}
function formatDate(date, fmt = 'yyyy-MM-dd HH:mm:ss') {
  const d = parseDate(date) || new Date();
  const map = {
    yyyy: String(d.getFullYear()),
    MM: padZero(d.getMonth() + 1),
    dd: padZero(d.getDate()),
    HH: padZero(d.getHours()),
    mm: padZero(d.getMinutes()),
    ss: padZero(d.getSeconds()),
    SSS: padZero(d.getMilliseconds(), 3),
  };
  return String(fmt)
    .replace(/yyyy/g, map.yyyy)
    .replace(/MM/g, map.MM)
    .replace(/dd/g, map.dd)
    .replace(/HH/g, map.HH)
    .replace(/mm/g, map.mm)
    .replace(/ss/g, map.ss)
    .replace(/SSS/g, map.SSS);
}
function addDays(date, days = 0) {
  const d = parseDate(date) || new Date();
  const x = new Date(d.getTime());
  x.setDate(x.getDate() + toInt(days, 0));
  return x;
}
function startOfDay(date) {
  const d = parseDate(date) || new Date();
  return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 0, 0, 0, 0);
}
function endOfDay(date) {
  const d = parseDate(date) || new Date();
  return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59, 999);
}
function startOfWeek(date, weekStartsOn = 1) {
  const d = startOfDay(date);
  const day = d.getDay(); // 0 Sun..6 Sat
  const ws = clamp(weekStartsOn, 0, 6);
  const diff = (day - ws + 7) % 7;
  d.setDate(d.getDate() - diff);
  return d;
}
function startOfMonth(date) {
  const d = parseDate(date) || new Date();
  return new Date(d.getFullYear(), d.getMonth(), 1, 0, 0, 0, 0);
}
function diffMs(a, b) {
  const da = parseDate(a) || new Date();
  const db = parseDate(b) || new Date();
  return da.getTime() - db.getTime();
}
function fromNow(date, { justNowSec = 10, suffix = '前', fixedDay = true } = {}) {
  const d = parseDate(date);
  if (!d) return '';
  const diff = Date.now() - d.getTime();
  if (diff < 0) return '刚刚';
  const sec = Math.floor(diff / 1000);
  if (sec < justNowSec) return '刚刚';
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}分钟${suffix}`;
  const hour = Math.floor(min / 60);
  if (hour < 24) return `${hour}小时${suffix}`;
  const day = Math.floor(hour / 24);
  if (fixedDay && day === 1) return '昨天';
  if (fixedDay && day === 2) return '前天';
  if (day < 30) return `${day}天${suffix}`;
  const month = Math.floor(day / 30);
  if (month < 12) return `${month}个月${suffix}`;
  const year = Math.floor(month / 12);
  return `${year}年${suffix}`;
}

function sleep(ms = 0) {
  const t = Math.max(0, toInt(ms, 0));
  return new Promise((resolve) => setTimeout(resolve, t));
}
// Not recommended in UI thread, but sometimes needed for quick debug
function blockSleep(ms = 0) {
  const t = Math.max(0, toInt(ms, 0));
  const end = Date.now() + t;
  while (Date.now() < end) {}
}

// function control
function debounce(fn, wait = 300, { leading = false, trailing = true } = {}) {
  let timer = null;
  let lastArgs;
  return function (...args) {
    lastArgs = args;
    if (timer) clearTimeout(timer);
    if (leading && !timer) fn.apply(this, args);
    timer = setTimeout(() => {
      timer = null;
      if (trailing && (!leading || lastArgs !== args)) fn.apply(this, lastArgs);
      lastArgs = null;
    }, Math.max(0, toInt(wait, 0)));
  };
}
function throttle(fn, wait = 300, { leading = true, trailing = true } = {}) {
  let last = 0;
  let timer = null;
  let lastArgs;
  return function (...args) {
    const nowT = Date.now();
    lastArgs = args;
    if (!last && !leading) last = nowT;
    const remaining = wait - (nowT - last);
    if (remaining <= 0 || remaining > wait) {
      if (timer) { clearTimeout(timer); timer = null; }
      last = nowT;
      fn.apply(this, args);
    } else if (trailing && !timer) {
      timer = setTimeout(() => {
        timer = null;
        last = leading ? Date.now() : 0;
        fn.apply(this, lastArgs);
      }, remaining);
    }
  };
}
function once(fn) {
  let called = false;
  let res;
  return function (...args) {
    if (called) return res;
    called = true;
    res = fn.apply(this, args);
    return res;
  };
}

// url
function parseQuery(query) {
  const q = String(query ?? '').replace(/^\?/, '');
  const out = {};
  if (!q) return out;
  q.split('&').forEach((kv) => {
    if (!kv) return;
    const [k, v = ''] = kv.split('=');
    const key = decodeURIComponent(k || '');
    const val = decodeURIComponent(v || '');
    if (!key) return;
    if (_hasOwn.call(out, key)) {
      const cur = out[key];
      out[key] = isArray(cur) ? cur.concat(val) : [cur, val];
    } else {
      out[key] = val;
    }
  });
  return out;
}
function stringifyQuery(obj) {
  const o = isObject(obj) ? obj : {};
  const pairs = [];
  Object.keys(o).forEach((k) => {
    const v = o[k];
    if (v === undefined) return;
    if (v === null) { pairs.push(`${encodeURIComponent(k)}=`); return; }
    if (isArray(v)) v.forEach((it) => pairs.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(it))}`));
    else pairs.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  });
  return pairs.length ? '?' + pairs.join('&') : '';
}
function joinUrl(baseUrl, path, query) {
  const b = String(baseUrl ?? '').replace(/\/+$/, '');
  const p = String(path ?? '').replace(/^\/+/, '');
  return b + (p ? '/' + p : '') + (query ? stringifyQuery(query) : '');
}

// validate
function isEmail(v) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(v ?? '').trim()); }
function isPhoneCN(v) { return /^1[3-9]\d{9}$/.test(String(v ?? '').trim()); }
function isUrl(v) {
  const s = String(v ?? '').trim();
  try { new URL(s); return true; } catch (_) { return /^https?:\/\/.+/i.test(s); }
}
function luhnCheck(num) {
  const s = String(num ?? '').replace(/\s+/g, '');
  if (!/^\d+$/.test(s)) return false;
  let sum = 0, odd = false;
  for (let i = s.length - 1; i >= 0; i--) {
    let d = s.charCodeAt(i) - 48;
    if (odd) { d *= 2; if (d > 9) d -= 9; }
    sum += d;
    odd = !odd;
  }
  return sum % 10 === 0;
}
function isBankCard(v) { return luhnCheck(v); }
function isHexColor(v) { return /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(String(v ?? '').trim()); }

// color
function hexToRgb(hex) {
  let s = String(hex ?? '').trim();
  if (!isHexColor(s)) return null;
  if (s.length === 4) s = '#' + s[1] + s[1] + s[2] + s[2] + s[3] + s[3];
  const n = parseInt(s.slice(1), 16);
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
}
function rgbToHex(r, g, b) {
  const toHex = (n) => padZero(clamp(toInt(n, 0), 0, 255).toString(16), 2);
  return '#' + toHex(r) + toHex(g) + toHex(b);
}
function randomHexColor() {
  return rgbToHex(randomInt(0, 255), randomInt(0, 255), randomInt(0, 255));
}
function mixColor(hexA, hexB, weight = 0.5) {
  const a = hexToRgb(hexA); const b = hexToRgb(hexB);
  if (!a || !b) return null;
  const w = clamp(toNumber(weight, 0.5), 0, 1);
  const r = Math.round(a.r * (1 - w) + b.r * w);
  const g = Math.round(a.g * (1 - w) + b.g * w);
  const bb = Math.round(a.b * (1 - w) + b.b * w);
  return rgbToHex(r, g, bb);
}
function lighten(hex, amount = 0.12) { return mixColor(hex, '#ffffff', amount) || String(hex ?? ''); }
function darken(hex, amount = 0.12) { return mixColor(hex, '#000000', amount) || String(hex ?? ''); }

// storage
function setStorage(key, value, { expireMs } = {}) {
  const k = String(key ?? '');
  const payload = isDef(expireMs)
    ? { v: value, e: Date.now() + Math.max(0, toInt(expireMs, 0)) }
    : { v: value };
  try { uni.setStorageSync(k, payload); return true; } catch (_) { return false; }
}
function getStorage(key, fallback) {
  const k = String(key ?? '');
  try {
    const payload = uni.getStorageSync(k);
    if (!payload) return fallback;
    if (isObject(payload) && _hasOwn.call(payload, 'e')) {
      if (Date.now() > payload.e) { uni.removeStorageSync(k); return fallback; }
    }
    return isObject(payload) && _hasOwn.call(payload, 'v') ? payload.v : payload;
  } catch (_) { return fallback; }
}
function removeStorage(key) { try { uni.removeStorageSync(String(key ?? '')); return true; } catch (_) { return false; } }
function clearStorage() { try { uni.clearStorageSync(); return true; } catch (_) { return false; } }

// device/platform helpers
function getSystemInfo() {
  try { return uni.getSystemInfoSync(); } catch (_) { return {}; }
}
function getPlatform() {
  const info = getSystemInfo();
  return info.platform || '';
}
function isH5() { return getPlatform() === 'web'; }
function isIOS() { return /ios/i.test(getPlatform()) || /iphone|ipad|ipod/i.test(getSystemInfo().model || ''); }
function isAndroid() { return /android/i.test(getPlatform()); }

// clipboard
function copyText(text) {
  return new Promise((resolve) => {
    const data = String(text ?? '');
    try {
      uni.setClipboardData({
        data,
        success: () => resolve(true),
        fail: () => resolve(false),
      });
    } catch (_) {
      resolve(false);
    }
  });
}

// base64 / file helpers (best-effort, cross-platform)
function _stripDataUrl(b64) {
  const s = String(b64 ?? '');
  const idx = s.indexOf('base64,');
  return idx >= 0 ? s.slice(idx + 7) : s;
}
function readFileAsBase64(filePath) {
  const path = String(filePath ?? '');
  if (!path) return Promise.resolve('');
  // already base64
  if (/^data:.*;base64,/.test(path)) return Promise.resolve(_stripDataUrl(path));
  return new Promise((resolve) => {
    try {
      const fs = uni.getFileSystemManager && uni.getFileSystemManager();
      if (!fs || !fs.readFile) return resolve('');
      fs.readFile({
        filePath: path,
        encoding: 'base64',
        success: (res) => resolve(res.data || ''),
        fail: () => resolve(''),
      });
    } catch (_) { resolve(''); }
  });
}
function saveBase64ToTempFile(base64, { ext = 'png', prefix = 'zutils_' } = {}) {
  const b64 = _stripDataUrl(base64);
  return new Promise((resolve) => {
    try {
      const fs = uni.getFileSystemManager && uni.getFileSystemManager();
      if (!fs || !fs.writeFile) return resolve('');
      const fileName = `${prefix}${Date.now()}_${randomInt(1000, 9999)}.${ext.replace('.', '')}`;
      const target = (uni.env && uni.env.USER_DATA_PATH ? uni.env.USER_DATA_PATH : (getSystemInfo().userDataPath || '')) + '/' + fileName;
      fs.writeFile({
        filePath: target,
        data: b64,
        encoding: 'base64',
        success: () => resolve(target),
        fail: () => resolve(''),
      });
    } catch (_) { resolve(''); }
  });
}

// ui helpers
function toast(title, { icon = 'none', duration = 2000 } = {}) {
  try { uni.showToast({ title: String(title ?? ''), icon, duration }); } catch (_) {}
}
function loading(title = '加载中…', { mask = true } = {}) {
  try { uni.showLoading({ title: String(title ?? ''), mask }); } catch (_) {}
}
function hideLoading() { try { uni.hideLoading(); } catch (_) {} }

const zUtils = {
  // types
  isNil, isDef, isString, isNumber, isBoolean, isFunction, isArray, isDate, isObject, isPlainObject, isPromise,

  // number
  clamp, toNumber, toInt, round, padZero, randomInt, randomFloat, formatThousands, formatCurrency, parseCurrency,

  // string
  trim, trimAll, capitalize, lowerFirst, camelize, kebabize, snakeize, truncate, maskPhoneCN, maskEmail, escapeHtml, unescapeHtml, bytesLength,

  // array
  unique, uniqueBy, chunk, flatten, groupBy, sortBy, shuffle, sample, range, sum, sumBy,

  // object
  pick, omit, get, set, deepClone, deepMerge, isEqual,

  // date
  now, parseDate, formatDate, addDays, startOfDay, endOfDay, startOfWeek, startOfMonth, diffMs, fromNow,

  // function control
  debounce, throttle, once,

  // url
  parseQuery, stringifyQuery, joinUrl,

  // validate
  isEmail, isPhoneCN, isUrl, isBankCard, isHexColor,

  // color
  hexToRgb, rgbToHex, randomHexColor, lighten, darken, mixColor,

  // storage
  setStorage, getStorage, removeStorage, clearStorage,

  // platform
  getSystemInfo, getPlatform, isH5, isIOS, isAndroid,

  // clipboard
  copyText,

  // base64 / file
  readFileAsBase64, saveBase64ToTempFile,

  // ui
  toast, loading, hideLoading,
};

export default zUtils;
export {
  isNil, isDef, isString, isNumber, isBoolean, isFunction, isArray, isDate, isObject, isPlainObject, isPromise,
  clamp, toNumber, toInt, round, padZero, randomInt, randomFloat, formatThousands, formatCurrency, parseCurrency,
  trim, trimAll, capitalize, lowerFirst, camelize, kebabize, snakeize, truncate, maskPhoneCN, maskEmail, escapeHtml, unescapeHtml, bytesLength,
  unique, uniqueBy, chunk, flatten, groupBy, sortBy, shuffle, sample, range, sum, sumBy,
  pick, omit, get, set, deepClone, deepMerge, isEqual,
  now, parseDate, formatDate, addDays, startOfDay, endOfDay, startOfWeek, startOfMonth, diffMs, fromNow,
  debounce, throttle, once,
  parseQuery, stringifyQuery, joinUrl,
  isEmail, isPhoneCN, isUrl, isBankCard, isHexColor,
  hexToRgb, rgbToHex, randomHexColor, lighten, darken, mixColor,
  setStorage, getStorage, removeStorage, clearStorage,
  getSystemInfo, getPlatform, isH5, isIOS, isAndroid,
  copyText, readFileAsBase64, saveBase64ToTempFile,
  toast, loading, hideLoading,
};
