/**
 * 本地存储工具
 */
const KEYS = {
  LICENSE_KEY: 'zm_license_key',
  MACHINE_CODE: 'zm_machine_code',
  EXPIRE_TIME: 'zm_expire_time',
  ONLINE_ENABLED: 'zm_online_enabled',
  SERVER_URL: 'zm_server_url',
  SYNTH_URL: 'zm_synth_url',
  SYNTH_SECRET: 'zm_synth_secret',
  LIPVOICE_SIGN: 'zm_lipvoice_sign',
}

// 生成手机端唯一设备码
function generateMachineCode() {
  let code = uni.getStorageSync(KEYS.MACHINE_CODE)
  if (code) return code
  // 基于时间戳 + 随机数生成
  const ts = Date.now().toString(36)
  const rand = Math.random().toString(36).substring(2, 10)
  code = `MB-${ts}-${rand}`.toUpperCase()
  uni.setStorageSync(KEYS.MACHINE_CODE, code)
  return code
}

export function getMachineCode() {
  return generateMachineCode()
}

export function saveLicense(data) {
  uni.setStorageSync(KEYS.LICENSE_KEY, data.license_key || '')
  uni.setStorageSync(KEYS.EXPIRE_TIME, data.expire_time || '')
  uni.setStorageSync(KEYS.ONLINE_ENABLED, data.online_enabled || 0)
  if (data.synthesis_server_url) {
    uni.setStorageSync(KEYS.SYNTH_URL, data.synthesis_server_url)
  }
  if (data.synthesis_api_secret !== undefined) {
    uni.setStorageSync(KEYS.SYNTH_SECRET, data.synthesis_api_secret || '')
  }
  if (data.lipvoice_sign !== undefined) {
    uni.setStorageSync(KEYS.LIPVOICE_SIGN, data.lipvoice_sign || '')
  }
}

export function getLicenseKey() {
  return uni.getStorageSync(KEYS.LICENSE_KEY) || ''
}

export function getExpireTime() {
  return uni.getStorageSync(KEYS.EXPIRE_TIME) || ''
}

export function isOnlineEnabled() {
  return parseInt(uni.getStorageSync(KEYS.ONLINE_ENABLED) || '0') === 1
}

export function isLoggedIn() {
  return !!getLicenseKey()
}

export function logout() {
  uni.removeStorageSync(KEYS.LICENSE_KEY)
  uni.removeStorageSync(KEYS.EXPIRE_TIME)
  uni.removeStorageSync(KEYS.ONLINE_ENABLED)
  uni.removeStorageSync(KEYS.SYNTH_URL)
  uni.removeStorageSync(KEYS.SYNTH_SECRET)
  uni.removeStorageSync(KEYS.LIPVOICE_SIGN)
}

export function getServerUrl() {
  return uni.getStorageSync(KEYS.SERVER_URL) || 'https://api.zhimengai.xyz'
}

export function setServerUrl(url) {
  uni.setStorageSync(KEYS.SERVER_URL, url)
}

export function getSynthUrl() {
  return uni.getStorageSync(KEYS.SYNTH_URL) || ''
}

export function getSynthSecret() {
  return uni.getStorageSync(KEYS.SYNTH_SECRET) || ''
}

export function getLipvoiceSign() {
  return uni.getStorageSync(KEYS.LIPVOICE_SIGN) || 'KVcC3FvZunYE4KimHhqkUxE4GxyV3Rqm'
}
