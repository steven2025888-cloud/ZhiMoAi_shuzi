/**
 * z-icon 图标预加载工具
 * 在应用启动时预先加载常用图标，实现立即显示
 *
 * 使用方法：
 * 1. 在 App.vue 的 onLaunch 中调用
 * 2. import { preloadIcons, preloadCommonIcons } from '@/uni_modules/zhimo-ui/components/z-icon/preload.js'
 * 3. preloadIcons(['mdi:home', 'mdi:account', ...])  // 预加载指定图标
 * 4. preloadCommonIcons()  // 预加载常用图标
 */

// 全局图标缓存（与 z-icon 组件共享）
// #ifdef H5
if (typeof window !== 'undefined') {
  window.__ZICON_CACHE__ = window.__ZICON_CACHE__ || {}
}
// #endif

// 获取缓存对象
function getCache() {
  // #ifdef H5
  if (typeof window !== 'undefined') {
    return window.__ZICON_CACHE__
  }
  // #endif
  return {}
}

// 设置缓存
function setCache(name, svg) {
  // #ifdef H5
  if (typeof window !== 'undefined') {
    window.__ZICON_CACHE__[name] = svg
  }
  // #endif

  // 同时存储到 localStorage 持久化
  try {
    const storageKey = `zicon_${name}`
    uni.setStorageSync(storageKey, svg)
  } catch (e) {
    // 忽略存储错误
  }
}

// 从缓存获取
function getFromCache(name) {
  // #ifdef H5
  if (typeof window !== 'undefined' && window.__ZICON_CACHE__[name]) {
    return window.__ZICON_CACHE__[name]
  }
  // #endif

  // 尝试从 localStorage 获取
  try {
    const storageKey = `zicon_${name}`
    const cached = uni.getStorageSync(storageKey)
    if (cached) {
      // 同步到内存缓存
      // #ifdef H5
      if (typeof window !== 'undefined') {
        window.__ZICON_CACHE__[name] = cached
      }
      // #endif
      return cached
    }
  } catch (e) {
    // 忽略读取错误
  }

  return null
}

/**
 * 获取单个图标的 SVG
 * @param {string} name - 图标名称，如 'mdi:home'
 * @returns {Promise<string|null>}
 */
async function fetchIcon(name) {
  if (!name) return null

  // 检查缓存
  const cached = getFromCache(name)
  if (cached) {
    return cached
  }

  const parts = name.split(':')
  if (parts.length !== 2) return null
  const [prefix, iconName] = parts

  try {
    // #ifdef APP-PLUS || H5
    const url = `https://api.iconify.design/${prefix}/${iconName}.svg`
    const response = await fetch(url)
    if (!response.ok) return null

    const svgText = await response.text()
    // 缓存结果
    setCache(name, svgText)
    return svgText
    // #endif

    // #ifdef MP
    // 小程序使用 uni.request
    return new Promise((resolve) => {
      uni.request({
        url: `https://api.iconify.design/${prefix}/${iconName}.svg`,
        success: (res) => {
          if (res.statusCode === 200 && res.data) {
            setCache(name, res.data)
            resolve(res.data)
          } else {
            resolve(null)
          }
        },
        fail: () => resolve(null)
      })
    })
    // #endif
  } catch (e) {
    console.warn('Failed to fetch icon:', name, e)
    return null
  }
}

/**
 * 预加载指定图标列表
 * @param {string[]} icons - 图标名称数组
 * @param {object} options - 配置选项
 * @param {number} options.concurrency - 并发数，默认 5
 * @param {function} options.onProgress - 进度回调 (loaded, total)
 * @param {function} options.onComplete - 完成回调
 * @returns {Promise<void>}
 */
export async function preloadIcons(icons, options = {}) {
  if (!icons || !icons.length) return

  const {
    concurrency = 5,
    onProgress = null,
    onComplete = null
  } = options

  let loaded = 0
  const total = icons.length

  // 分批并发加载
  const chunks = []
  for (let i = 0; i < icons.length; i += concurrency) {
    chunks.push(icons.slice(i, i + concurrency))
  }

  for (const chunk of chunks) {
    await Promise.all(
      chunk.map(async (name) => {
        await fetchIcon(name)
        loaded++
        if (onProgress) {
          onProgress(loaded, total)
        }
      })
    )
  }

  if (onComplete) {
    onComplete()
  }

  console.log(`[z-icon] 预加载完成: ${loaded}/${total} 个图标`)
}

/**
 * 预加载常用图标
 * 包含 Material Design Icons 中最常用的图标
 */
export async function preloadCommonIcons(options = {}) {
  const commonIcons = [
    // 导航相关
    'mdi:home',
    'mdi:home-outline',
    'mdi:menu',
    'mdi:arrow-left',
    'mdi:arrow-right',
    'mdi:chevron-left',
    'mdi:chevron-right',
    'mdi:chevron-up',
    'mdi:chevron-down',
    'mdi:close',
    'mdi:check',

    // 用户相关
    'mdi:account',
    'mdi:account-outline',
    'mdi:account-circle',
    'mdi:account-circle-outline',

    // 操作相关
    'mdi:plus',
    'mdi:minus',
    'mdi:delete',
    'mdi:delete-outline',
    'mdi:pencil',
    'mdi:pencil-outline',
    'mdi:magnify',
    'mdi:refresh',
    'mdi:share',
    'mdi:share-variant',
    'mdi:download',
    'mdi:upload',
    'mdi:copy',

    // 状态相关
    'mdi:check-circle',
    'mdi:check-circle-outline',
    'mdi:alert-circle',
    'mdi:alert-circle-outline',
    'mdi:information',
    'mdi:information-outline',
    'mdi:help-circle',
    'mdi:help-circle-outline',

    // 常用功能
    'mdi:heart',
    'mdi:heart-outline',
    'mdi:star',
    'mdi:star-outline',
    'mdi:bell',
    'mdi:bell-outline',
    'mdi:cog',
    'mdi:cog-outline',
    'mdi:email',
    'mdi:email-outline',
    'mdi:phone',
    'mdi:phone-outline',
    'mdi:camera',
    'mdi:camera-outline',
    'mdi:image',
    'mdi:image-outline',

    // 媒体控制
    'mdi:play',
    'mdi:pause',
    'mdi:stop',
    'mdi:skip-next',
    'mdi:skip-previous',
    'mdi:volume-high',
    'mdi:volume-off',

    // 其他常用
    'mdi:cart',
    'mdi:cart-outline',
    'mdi:map-marker',
    'mdi:map-marker-outline',
    'mdi:calendar',
    'mdi:calendar-outline',
    'mdi:clock',
    'mdi:clock-outline',
    'mdi:eye',
    'mdi:eye-outline',
    'mdi:eye-off',
    'mdi:eye-off-outline',
    'mdi:lock',
    'mdi:lock-outline',
    'mdi:lock-open',
    'mdi:lock-open-outline',
    'mdi:wifi',
    'mdi:wifi-off',
    'mdi:bluetooth',
    'mdi:qrcode',
    'mdi:qrcode-scan',
    'mdi:filter',
    'mdi:filter-outline',
    'mdi:sort',
    'mdi:dots-vertical',
    'mdi:dots-horizontal',
    'mdi:more',
    'mdi:fullscreen',
    'mdi:fullscreen-exit'
  ]

  return preloadIcons(commonIcons, options)
}

/**
 * 预加载自定义图标集
 * @param {string} prefix - 图标前缀，如 'mdi'
 * @param {string[]} names - 图标名称数组（不含前缀）
 */
export async function preloadIconSet(prefix, names, options = {}) {
  const icons = names.map(name => `${prefix}:${name}`)
  return preloadIcons(icons, options)
}

/**
 * 清除图标缓存
 */
export function clearIconCache() {
  // #ifdef H5
  if (typeof window !== 'undefined') {
    window.__ZICON_CACHE__ = {}
  }
  // #endif

  // 清除 localStorage 中的图标缓存
  try {
    const keys = uni.getStorageInfoSync().keys || []
    keys.forEach(key => {
      if (key.startsWith('zicon_')) {
        uni.removeStorageSync(key)
      }
    })
  } catch (e) {
    // 忽略错误
  }

  console.log('[z-icon] 缓存已清除')
}

/**
 * 获取已缓存的图标数量
 */
export function getCachedIconCount() {
  let count = 0

  // #ifdef H5
  if (typeof window !== 'undefined' && window.__ZICON_CACHE__) {
    count = Object.keys(window.__ZICON_CACHE__).length
  }
  // #endif

  return count
}

// 导出获取图标方法供组件使用
export { fetchIcon, getFromCache, setCache }
