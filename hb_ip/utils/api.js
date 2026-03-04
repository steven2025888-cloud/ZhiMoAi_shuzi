/**
 * HTTP API 工具
 * PHP服务器：登录 / TTS
 * 合成服务器(run_server.py)：资产管理 / 视频合成 / 视频编辑
 */
import { getLicenseKey, getMachineCode, getServerUrl, getSynthUrl, getSynthSecret, getLipvoiceSign, getSessionToken } from './storage.js'
import { sendGpuBootRequest } from './websocket.js'

// ── PHP 服务器请求 ──
function request(path, options = {}) {
  // 修复：移除 baseUrl 末尾的斜杠，避免双斜杠问题
  const baseUrl = getServerUrl().replace(/\/+$/, '')
  const url = `${baseUrl}${path}`
  const licenseKey = getLicenseKey()
  const machineCode = getMachineCode()
  const sessionToken = getSessionToken()

  return new Promise((resolve, reject) => {
    uni.request({
      url,
      method: options.method || 'POST',
      header: {
        'Content-Type': 'application/json',
        'Authorization': licenseKey ? `Bearer ${licenseKey}` : '',
        'X-Machine-Code': machineCode,
        'X-Device-Type': 'mobile',
        ...(sessionToken ? { 'X-Session-Token': sessionToken } : {}),
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

  if (url.includes('lipvoice.cn')) {
    if (lipvoiceSign) {
      // sign 同时加到 URL 参数和 header，确保兼容
      const sep = url.includes('?') ? '&' : '?'
      url = `${url}${sep}sign=${encodeURIComponent(lipvoiceSign)}`
      console.log('[下载] 使用sign直接下载:', url)
    } else {
      // 没有 sign，走服务器代理
      console.log('[下载] 没有sign，使用代理下载')
      const baseUrl = getServerUrl().replace(/\/+$/, '')
      url = `${baseUrl}/api/dsp/voice/tts/download?voice_url=${encodeURIComponent(url)}`
    }
  }

  const sessionToken = getSessionToken()

  return new Promise((resolve, reject) => {
    uni.downloadFile({
      url,
      timeout,
      header: {
        'Authorization': licenseKey ? `Bearer ${licenseKey}` : '',
        'X-Machine-Code': machineCode,
        'X-Device-Type': 'mobile',
        ...(sessionToken ? { 'X-Session-Token': sessionToken } : {}),
        ...(lipvoiceSign ? { 'sign': lipvoiceSign } : {}),
      },
      success: (res) => {
        console.log('[下载] 结果:', res.statusCode, res.tempFilePath ? '有文件' : '无文件')
        if (res.statusCode === 200 && res.tempFilePath) resolve(res)
        else reject(new Error(`下载失败 HTTP ${res.statusCode}`))
      },
      fail: (err) => {
        console.error('[下载] 网络错误:', err)
        reject(new Error(err.errMsg || '下载失败'))
      },
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
          // 解析服务器返回的错误消息（如 404 文件不存在、401 鉴权失败等）
          let errMsg = `HTTP ${res.statusCode}`
          try {
            const d = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
            if (d && d.msg) errMsg = d.msg
          } catch (e) { /* ignore */ }
          reject(new Error(errMsg))
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
  const sessionToken = getSessionToken()

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
        ...(sessionToken ? { 'X-Session-Token': sessionToken } : {}),
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

// AI 文案优化
export function aiOptimizeText(text) {
  return request('/api/dsp/ai/optimize-text', {
    data: { text },
    timeout: 60000,
  })
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
  const sessionToken = getSessionToken()

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
        ...(sessionToken ? { 'X-Session-Token': sessionToken } : {}),
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

// 直连 GPU 服务器上传资产（跨过 PHP，适用于 GPU 在线时）
export function synthUploadAsset(filePath, assetType, name) {
  const baseUrl = getSynthUrl()
  if (!baseUrl) return Promise.reject(new Error('合成服务器未配置'))
  const secret = getSynthSecret()
  const licenseKey = getLicenseKey()

  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: `${baseUrl.replace(/\/+$/, '')}/api/asset/upload`,
      filePath,
      name: 'file',
      formData: {
        asset_type: assetType,
        name: name,
        license_key: licenseKey || '',
      },
      header: {
        ...(secret ? { 'Authorization': `Bearer ${secret}` } : {}),
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

// ── GPU 电源管理 ──

// 纯状态检查（不触发开机），用于页面初始化等只需要显示状态的场景
export async function gpuStatusCheck() {
  const synthUrl = getSynthUrl()
  if (synthUrl) {
    try {
      const direct = await synthRequest('/api/heygem/health', { method: 'GET', timeout: 5000 })
      if (direct && direct.code === 0) {
        console.log('[GPU] 状态检查: 在线')
        return { code: 0, data: { online: true }, msg: 'GPU在线' }
      }
    } catch (e) {
      console.log('[GPU] 状态检查: 离线 -', e.message)
    }
  }
  return { code: -1, data: { online: false }, msg: 'GPU离线' }
}

// 检查 GPU 状态 + 离线时自动发送开机请求（用于需要 GPU 的操作：合成、上传数字人等）
export async function gpuStatus() {
  // 先做纯检查
  const checkRes = await gpuStatusCheck()
  if (checkRes.data && checkRes.data.online) {
    return checkRes
  }
  // 离线 → 发送开机请求
  const bootReqId = sendGpuBootRequest()
  const licenseKey = getLicenseKey()
  try {
    const proxyRes = await request('/api/heygem/health/proxy', {
      method: 'POST',
      data: { license_key: licenseKey },
      timeout: 10000,
    })
    console.log('[GPU] health/proxy 返回:', JSON.stringify(proxyRes))
  } catch (e) {
    console.log('[GPU] health/proxy 调用失败:', e.message)
  }
  console.log(`[GPU] 状态: 离线，已发送开机请求 (boot_request=${bootReqId || 'ws未连接'})`)
  return { code: -1, data: { online: false }, msg: 'GPU离线' }
}

// 请求开机（显式调用）
export async function gpuPowerOn() {
  return gpuStatus()
}

// 轮询等待 GPU 上线（直连 GPU HTTP 健康检查）
export async function waitForGpuOnline(maxWaitMs = 1800000, pollIntervalMs = 5000) {
  const startTime = Date.now()
  while (Date.now() - startTime < maxWaitMs) {
    try {
      const res = await gpuStatus()
      if (res.data && res.data.online) {
        return { success: true, data: res.data }
      }
    } catch (e) {
      console.log('[GPU] 状态检查失败:', e.message)
    }
    const elapsed = Math.round((Date.now() - startTime) / 1000)
    console.log(`[GPU] 等待中... ${elapsed}s / ${maxWaitMs / 1000}s`)
    await new Promise(r => setTimeout(r, pollIntervalMs))
  }
  return { success: false, error: 'GPU 开机超时' }
}

// ── HeyGem 在线合成 ──
// 健康检查：优先直连 GPU，失败则走 PHP 代理
export async function heygemHealth() {
  // 先尝试直连 GPU 服务器
  const synthUrl = getSynthUrl()
  if (synthUrl) {
    try {
      const direct = await synthRequest('/api/heygem/health', { method: 'GET', timeout: 5000 })
      if (direct && direct.code === 0) return direct
    } catch (e) {
      console.log('[HeyGem] 直连健康检查失败，走代理:', e.message)
    }
  }
  // 回退到 PHP 代理
  const proxy = await gpuStatus()
  if (proxy.data && proxy.data.online) {
    return { code: 0, data: { initialized: true }, msg: 'GPU 在线（代理）' }
  }
  return { code: -1, msg: proxy.msg || 'GPU 离线' }
}

// 任务提交：优先直连 GPU，失败则走 PHP 代理（支持离线排队）
export async function heygemSubmitByHash(audioHash, audioExt, videoHash, videoExt) {
  const synthUrl = getSynthUrl()
  const licenseKey = getLicenseKey()  // WS 进度推送路由用
  // 先尝试直连 GPU
  if (synthUrl) {
    try {
      const direct = await synthRequest('/api/heygem/submit', {
        data: { audio_hash: audioHash, audio_ext: audioExt, video_hash: videoHash, video_ext: videoExt, license_key: licenseKey },
        timeout: 30000,
      })
      if (direct && direct.code === 0) return direct
    } catch (e) {
      console.log('[HeyGem] 直连提交失败，走代理:', e.message)
    }
  }
  // 回退到 PHP 代理（HeyGemTaskController::submit，支持离线排队）
  return request('/api/heygem/task/submit', {
    data: { audio_hash: audioHash, audio_ext: audioExt, video_hash: videoHash, video_ext: videoExt, license_key: licenseKey },
    timeout: 30000,
  })
}

// 进度查询：优先直连 GPU，失败则走 PHP 代理
export async function heygemProgress(taskId) {
  const synthUrl = getSynthUrl()
  if (synthUrl) {
    try {
      const direct = await synthRequest(`/api/heygem/progress?task_id=${taskId}`, {
        method: 'GET', timeout: 15000,
      })
      if (direct) return direct
    } catch (e) {
      console.log('[HeyGem] 直连进度查询失败，走代理:', e.message)
    }
  }
  // 回退到 PHP 代理
  return request('/api/heygem/task/status', {
    method: 'GET',
    data: { task_id: taskId },
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

// 上传文件到 GPU 文件池（返回 hash）
export async function uploadFileToPool(filePath) {
  const baseUrl = getSynthUrl()
  if (!baseUrl) throw new Error('合成服务器未配置')
  const secret = getSynthSecret()

  // 先计算文件 hash（用随机临时 hash）
  const tmpHash = `tmp_${Date.now()}_${Math.random().toString(36).substring(2, 10)}`
  const ext = '.mp4'

  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: `${baseUrl}/api/heygem/upload_file`,
      filePath,
      name: 'file',
      formData: { hash: tmpHash, ext },
      header: secret ? { 'Authorization': `Bearer ${secret}` } : {},
      timeout: 600000,
      success(res) {
        if (res.statusCode === 200) {
          const data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
          resolve(data) // { code: 0, data: { hash, server_path } }
        } else {
          reject(new Error(`Upload HTTP ${res.statusCode}`))
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
