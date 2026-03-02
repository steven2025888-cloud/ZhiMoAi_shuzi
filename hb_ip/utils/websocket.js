/**
 * WebSocket 客户端工具
 * 手机端通过 WS 与服务器通信，服务器中转给 PC 端
 */
import { getLicenseKey, getServerUrl } from './storage.js'

let _ws = null
let _connected = false
let _registered = false
let _heartbeatTimer = null
let _reconnectTimer = null
let _reconnectCount = 0
const MAX_RECONNECT = 10
const HEARTBEAT_INTERVAL = 25000

// 消息回调
const _handlers = {}

/**
 * 注册消息处理器
 * @param {string} type 消息类型
 * @param {Function} handler 处理函数
 */
export function on(type, handler) {
  if (!_handlers[type]) _handlers[type] = []
  _handlers[type].push(handler)
}

/**
 * 移除消息处理器
 */
export function off(type, handler) {
  if (!_handlers[type]) return
  if (handler) {
    _handlers[type] = _handlers[type].filter(h => h !== handler)
  } else {
    delete _handlers[type]
  }
}

function _emit(type, data) {
  const handlers = _handlers[type] || []
  handlers.forEach(h => {
    try { h(data) } catch (e) { console.error('[WS] handler error:', e) }
  })
  // 通用 * 监听
  const allHandlers = _handlers['*'] || []
  allHandlers.forEach(h => {
    try { h({ type, ...data }) } catch (e) { console.error('[WS] * handler error:', e) }
  })
}

/**
 * 连接 WebSocket
 */
export function connect() {
  if (_ws && _connected) return

  const serverUrl = getServerUrl()
  // http → ws, https → wss
  const wsUrl = serverUrl.replace(/^https/, 'wss').replace(/\/$/, '') + '/dsp'

  console.log('[WS] 连接:', wsUrl)

  _ws = uni.connectSocket({
    url: wsUrl,
    complete: () => {},
  })

  uni.onSocketOpen(() => {
    console.log('[WS] 已连接')
    _connected = true
    _reconnectCount = 0
    _startHeartbeat()
    _register()
    _emit('open', {})
  })

  uni.onSocketMessage((res) => {
    try {
      const data = JSON.parse(res.data)
      const type = data.type || ''
      console.log('[WS] 收到:', type, JSON.stringify(data).substring(0, 200))
      _emit(type, data)
    } catch (e) {
      console.error('[WS] 解析失败:', res.data)
    }
  })

  uni.onSocketClose(() => {
    console.log('[WS] 断开')
    _connected = false
    _registered = false
    _stopHeartbeat()
    _emit('close', {})
    _scheduleReconnect()
  })

  uni.onSocketError((err) => {
    console.error('[WS] 错误:', err)
    _connected = false
    _registered = false
    _emit('error', err)
  })
}

function _register() {
  const key = getLicenseKey()
  if (!key) return
  send({
    type: 'register',
    key: key,
    device_type: 'mobile',
  })
  _registered = true
}

function _startHeartbeat() {
  _stopHeartbeat()
  _heartbeatTimer = setInterval(() => {
    if (_connected) {
      send({ type: 'ping' })
    }
  }, HEARTBEAT_INTERVAL)
}

function _stopHeartbeat() {
  if (_heartbeatTimer) {
    clearInterval(_heartbeatTimer)
    _heartbeatTimer = null
  }
}

function _scheduleReconnect() {
  if (_reconnectTimer) return
  if (_reconnectCount >= MAX_RECONNECT) {
    console.log('[WS] 达到最大重连次数')
    _emit('max_reconnect', {})
    return
  }
  const delay = Math.min(2000 * Math.pow(1.5, _reconnectCount), 30000)
  _reconnectCount++
  console.log(`[WS] ${delay}ms 后重连 (第${_reconnectCount}次)`)
  _reconnectTimer = setTimeout(() => {
    _reconnectTimer = null
    connect()
  }, delay)
}

/**
 * 发送消息
 */
export function send(data) {
  if (!_connected) {
    console.warn('[WS] 未连接，无法发送')
    return false
  }
  uni.sendSocketMessage({
    data: JSON.stringify(data),
  })
  return true
}

/**
 * 发送手机端任务给 PC 端
 * @param {string} taskType subtitle|pip|bgm|publish|full_process
 * @param {object} payload 任务参数
 * @returns {string} requestId
 */
export function sendMobileTask(taskType, payload = {}) {
  const requestId = `mt_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`
  send({
    type: 'mobile_task',
    task_type: taskType,
    request_id: requestId,
    payload,
  })
  return requestId
}

/**
 * 发送同步消息给指定设备
 */
export function syncToDevice(targetDevice, syncData) {
  send({
    type: 'sync',
    target_device: targetDevice,
    ...syncData,
  })
}

/**
 * 断开连接
 */
export function disconnect() {
  _stopHeartbeat()
  if (_reconnectTimer) {
    clearTimeout(_reconnectTimer)
    _reconnectTimer = null
  }
  if (_ws) {
    uni.closeSocket()
    _ws = null
  }
  _connected = false
  _registered = false
}

export function isConnected() {
  return _connected
}

export function isRegistered() {
  return _registered
}
