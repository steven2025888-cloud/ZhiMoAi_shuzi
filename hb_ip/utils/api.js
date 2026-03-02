/**
 * HTTP API 工具
 * PHP服务器：登录 / TTS
 * 合成服务器(run_server.py)：资产管理 / 视频合成 / 视频编辑
 */
import { getLicenseKey, getMachineCode, getServerUrl, getSynthUrl, getSynthSecret, getLipvoiceSign } from './storage.js'

// ── PHP 服务器请求 ──
function request(path, options = {}) {
  // 修复：移除 baseUrl 末尾的斜杠，避免双斜杠问题
  const baseUrl = getServerUrl().replace(/\/+$/, '')
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

// ── 下载文件（带卡密鉴权，用于 uni.downloadFile） ──
export function downloadFileWithAuth(url, timeout = 60000) {
  const licenseKey = getLicenseKey()
  const machineCode = getMachineCode()
  const lipvoiceSign = getLipvoiceSign()

  // 如果没有sign，使用代理下载
  if (!lipvoiceSign && url.includes('lipvoice.cn')) {
    console.log('[下载] 没有sign，使用代理下载')
    const baseUrl = getServerUrl().replace(/\/+$/, '')
    url = `${baseUrl}/api/dsp/voice/tts/download?voice_url=${encodeURIComponent(url)}`
  } else if (lipvoiceSign) {
    console.log('[下载] 使用sign直接下载:', url)
  }

  return new Promise((resolve, reject) => {
    uni.downloadFile({
      url,
      timeout,
      header: {
        'Authorization': licenseKey ? `Bearer ${licenseKey}` : '',
        'X-Machine-Code': machineCode,
        'X-Device-Type': 'mobile',
        'sign': lipvoiceSign,
      },
      success: (res) => {
        if (res.statusCode === 200 && res.tempFilePath) resolve(res)
        else reject(new Error('下载失败'))
      },
      fail: reject,
    })
  })
}

// ── 合成服务器请求 (run_server.py) ──
function synthRequest(path, options = {}) {
  // 修复：移除 baseUrl 末尾的斜杠，避免双斜杠问题
  const baseUrl = getSynthUrl()
  if (!baseUrl) return Promise.reject(new Error('合成服务器未配置，请重新登录'))
  const url = `${baseUrl.replace(/\/+$/, '')}${path}`
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

// ── 语音模型 ──
export function listVoiceModels() {
  return request('/api/dsp/voice/model/list', { method: 'GET' })
}

export function uploadVoiceModel(filePath, name) {
  const baseUrl = getServerUrl()
  const licenseKey = getLicenseKey()
  const machineCode = getMachineCode()

  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: `${baseUrl}/api/dsp/voice/model/upload`,
      filePath,
      name: 'file',
      formData: { name },
      header: {
        'Authorization': licenseKey ? `Bearer ${licenseKey}` : '',
        'X-Machine-Code': machineCode,
        'X-Device-Type': 'mobile',
      },
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
  const baseUrl = getServerUrl().replace(/\/+$/, '')
  return `${baseUrl}/api/dsp/voice/tts/download?voice_url=${encodeURIComponent(voiceUrl)}`
}

// 查询合成记录列表
export function ttsHistory(page = 1, limit = 20) {
  return request('/api/dsp/voice/tts/history', {
    method: 'GET',
    data: { page, limit },
    timeout: 30000,
  })
}

// 查询合成记录详情
export function ttsHistoryDetail(id) {
  return request('/api/dsp/voice/tts/history/detail', {
    method: 'GET',
    data: { id },
    timeout: 30000,
  })
}

// ── 资产管理 ──
// uploadAsset：通过 API 端上传（GPU 离线时自动排队）
export function uploadAsset(filePath, assetType, name) {
  const licenseKey = getLicenseKey()
  const machineCode = getMachineCode()

  // 使用 API 端接口，而不是直接连接 GPU
  const baseUrl = getServerUrl().replace(/\/+$/, '')

  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: `${baseUrl}/api/asset/upload`,
      filePath,
      name: 'file',
      formData: {
        asset_type: assetType,
        name: name,
      },
      header: {
        'Authorization': licenseKey ? `Bearer ${licenseKey}` : '',
        'X-Machine-Code': machineCode,
        'X-Device-Type': 'mobile',
      },
      timeout: 600000,
      success(res) {
        if (res.statusCode === 200) {
          const data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
          resolve(data)
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
