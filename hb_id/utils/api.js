/**
 * HTTP API 工具
 * PHP服务器：登录 / TTS
 * 合成服务器(run_server.py)：资产管理 / 视频合成 / 视频编辑
 */
import { getLicenseKey, getMachineCode, getServerUrl, getSynthUrl, getSynthSecret } from './storage.js'

// ── PHP 服务器请求 ──
function request(path, options = {}) {
  const baseUrl = getServerUrl()
  const url = `${baseUrl}${path}`
  const licenseKey = getLicenseKey()
  const machineCode = getMachineCode()

  return new Promise((resolve, reject) => {
    uni.request({
      url,
      method: options.method || 'POST',
      header: {
        'Content-Type': 'application/json',
        'Authorization': licenseKey ? `Bearer ${licenseKey}` : '',
        'X-Machine-Code': machineCode,
        'X-Device-Type': 'mobile',
        ...(options.header || {}),
      },
      data: options.data || {},
      timeout: options.timeout || 30000,
      success(res) {
        if (res.statusCode === 200) {
          resolve(res.data)
        } else {
          reject(new Error(`HTTP ${res.statusCode}`))
        }
      },
      fail(err) {
        reject(err)
      },
    })
  })
}

// ── 合成服务器请求 (run_server.py) ──
function synthRequest(path, options = {}) {
  const baseUrl = getSynthUrl()
  if (!baseUrl) return Promise.reject(new Error('合成服务器未配置，请重新登录'))
  const url = `${baseUrl}${path}`
  const secret = getSynthSecret()

  return new Promise((resolve, reject) => {
    uni.request({
      url,
      method: options.method || 'POST',
      header: {
        'Content-Type': 'application/json',
        ...(secret ? { 'Authorization': `Bearer ${secret}` } : {}),
        ...(options.header || {}),
      },
      data: options.data || {},
      timeout: options.timeout || 30000,
      success(res) {
        if (res.statusCode === 200) {
          const d = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
          resolve(d)
        } else {
          reject(new Error(`HTTP ${res.statusCode}`))
        }
      },
      fail: reject,
    })
  })
}

// ── 卡密登录 ──
export function login(licenseKey) {
  const machineCode = getMachineCode()
  const baseUrl = getServerUrl()
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${baseUrl}/api/dsp/login`,
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: {
        license_key: licenseKey,
        machine_code: machineCode,
        device_type: 'mobile',
      },
      timeout: 15000,
      success(res) {
        if (res.statusCode === 200) resolve(res.data)
        else reject(new Error(`HTTP ${res.statusCode}`))
      },
      fail: reject,
    })
  })
}

// ── TTS 相关 ──
export function ttsCreate(text, modelId) {
  return request('/api/dsp/voice/tts', {
    data: { text, model_id: modelId },
    timeout: 60000,
  })
}

export function ttsResult(taskId) {
  return request('/api/dsp/voice/tts/result', {
    data: { taskId },
    timeout: 30000,
  })
}

export function ttsDownloadUrl(voiceUrl) {
  const baseUrl = getServerUrl()
  return `${baseUrl}/api/dsp/voice/tts/download?voice_url=${encodeURIComponent(voiceUrl)}`
}

// ── 资产管理 ──
// uploadAsset：直连 GPU 合成服务器（文件上传，需要直连性能）
export function uploadAsset(filePath, assetType, name) {
  const baseUrl = getSynthUrl()
  if (!baseUrl) return Promise.reject(new Error('合成服务器未配置'))
  const secret = getSynthSecret()
  const licenseKey = getLicenseKey()

  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: `${baseUrl}/api/asset/upload`,
      filePath,
      name: 'file',
      formData: {
        license_key: licenseKey,
        asset_type: assetType,
        name: name,
      },
      header: secret ? { 'Authorization': `Bearer ${secret}` } : {},
      timeout: 600000,
      success(res) {
        if (res.statusCode === 200) {
          resolve(typeof res.data === 'string' ? JSON.parse(res.data) : res.data)
        } else {
          reject(new Error(`Upload HTTP ${res.statusCode}`))
        }
      },
      fail: reject,
    })
  })
}

// listAssets / deleteAsset：走 PHP API 端（GPU 按需开机，API 常驻）
export function listAssets(assetType) {
  let path = '/api/asset/list'
  if (assetType) path += `?asset_type=${assetType}`
  return request(path, { method: 'GET' })
}

export function deleteAsset(assetId) {
  return request('/api/asset/delete', {
    data: { id: assetId },
  })
}

// ── HeyGem 在线合成（直连合成服务器） ──
export function heygemHealth() {
  return synthRequest('/api/heygem/health', { method: 'GET', timeout: 10000 })
}

export function heygemSubmitByHash(audioHash, audioExt, videoHash, videoExt) {
  return synthRequest('/api/heygem/submit', {
    data: { audio_hash: audioHash, audio_ext: audioExt, video_hash: videoHash, video_ext: videoExt },
    timeout: 30000,
  })
}

export function heygemProgress(taskId) {
  return synthRequest(`/api/heygem/progress?task_id=${taskId}`, {
    method: 'GET',
    timeout: 15000,
  })
}

export function heygemDownloadUrl(taskId) {
  const baseUrl = getSynthUrl()
  const secret = getSynthSecret()
  let url = `${baseUrl}/api/heygem/download?task_id=${taskId}`
  if (secret) url += `&token=${secret}`
  return url
}

// ── 视频编辑（直连合成服务器） ──
export function videoEditUpload(filePath, editType, formData = {}) {
  const baseUrl = getSynthUrl()
  if (!baseUrl) return Promise.reject(new Error('合成服务器未配置'))
  const secret = getSynthSecret()

  return new Promise((resolve, reject) => {
    const fd = { edit_type: editType, ...formData }
    uni.uploadFile({
      url: `${baseUrl}/api/video/edit`,
      filePath,
      name: 'video',
      formData: fd,
      header: secret ? { 'Authorization': `Bearer ${secret}` } : {},
      timeout: 600000,
      success(res) {
        if (res.statusCode === 200) {
          resolve(typeof res.data === 'string' ? JSON.parse(res.data) : res.data)
        } else {
          reject(new Error(`Edit HTTP ${res.statusCode}`))
        }
      },
      fail: reject,
    })
  })
}

export function videoEditDownloadUrl(taskId) {
  const baseUrl = getSynthUrl()
  return `${baseUrl}/api/video/edit/download?task_id=${taskId}`
}
