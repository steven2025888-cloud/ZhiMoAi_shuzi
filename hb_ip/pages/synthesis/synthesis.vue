<template>
  <view class="synth-page">
    <!-- 步骤1：音频 -->
    <view class="card">
      <view class="card-header">
        <view class="step-badge">1</view>
        <text class="card-title">音频</text>
      </view>

      <view v-if="ttsAudioUrl" class="audio-ready">
        <text class="ready-icon">✅</text>
        <view class="ready-info">
          <text class="ready-title">TTS合成音频</text>
          <text class="ready-desc">{{ ttsText || '语音合成结果' }}</text>
        </view>
        <z-button size="xs" type="light" text="清除" @click="clearTTSAudio" />
      </view>

      <view v-else class="audio-options">
        <z-button type="info" text="🎙️ 录音" round @click="startRecord" />
        <z-button type="light" text="📁 上传音频" round @click="chooseAudio" />
        <z-button type="purple" text="📝 去TTS" round @click="goTTS" />
      </view>

      <view v-if="localAudioPath" class="audio-ready" style="margin-top: 16rpx;">
        <text class="ready-icon">🎵</text>
        <text class="ready-title">{{ localAudioName }}</text>
        <z-button size="xs" type="success" text="▶" @click="playLocalAudio" />
      </view>

      <view v-if="recording" class="recording-bar">
        <text class="rec-dot">🔴</text>
        <text class="rec-text">录音中... {{ recordSeconds }}s</text>
        <z-button size="xs" type="danger" text="停止" @click="stopRecord" />
      </view>
    </view>

    <!-- 步骤2：选择数字人 -->
    <view class="card">
      <view class="card-header">
        <view class="step-badge">2</view>
        <text class="card-title">选择数字人</text>
        <z-button size="xs" type="light" text="刷新" @click="loadAvatars" />
        <z-button size="xs" type="primary" text="+ 上传" @click="uploadAvatar" style="margin-left: 12rpx;" />
      </view>

      <view v-if="avatarsLoading" class="loading-row">
        <text class="loading-text">加载中...</text>
      </view>

      <scroll-view v-else scroll-x class="avatar-scroll">
        <view class="avatar-list">
          <view
            v-for="av in avatars"
            :key="av.id"
            class="avatar-item"
            :class="{ active: selectedAvatar?.id === av.id }"
            @tap="selectedAvatar = av"
          >
            <view class="avatar-thumb">
              <text class="avatar-emoji">🎭</text>
            </view>
            <text class="avatar-name">{{ av.name }}</text>
            <text class="avatar-days">剩{{ av.days_left }}天</text>
          </view>
        </view>
      </scroll-view>

      <view v-if="!avatarsLoading && avatars.length === 0" class="empty-row">
        <text class="empty-text">暂无数字人，请点击"上传"添加视频</text>
      </view>

      <view v-if="avatarUploading" class="upload-bar">
        <text class="upload-text">上传数字人视频中...</text>
      </view>
    </view>

    <!-- 步骤3：合成 -->
    <view class="card">
      <view class="card-header">
        <view class="step-badge">3</view>
        <text class="card-title">在线合成</text>
        <view class="gpu-status" :class="gpuOnlineStatus">
          <text class="gpu-dot"></text>
          <text class="gpu-text">{{ localStatusText }}</text>
        </view>
      </view>

      <!-- 离线提示 -->
      <view v-if="gpuOnlineStatus === 'offline'" class="gpu-offline-tip">
        <text class="tip-icon">💡</text>
        <text class="tip-text">本地程序未就绪，点击合成将自动加载（预计两分钟）</text>
      </view>

      <z-button
        type="primary"
        size="lg"
        :text="synthesizing ? '合成中...' : '🚀 开始视频合成'"
        :loading="synthesizing"
        :disabled="synthesizing || !hasAudio || !selectedAvatar"
        block
        round
        @click="startSynthesis"
      />

      <view v-if="progressMsg" class="progress-info">
        <view class="progress-bar-inner" :style="{ width: progressPct + '%' }"></view>
        <text class="progress-label">{{ progressMsg }}</text>
      </view>
    </view>

    <!-- 合成结果 + 视频编辑 -->
    <view v-if="resultVideoUrl" class="card result-card">
      <view class="card-header">
        <text class="card-icon">🎬</text>
        <text class="card-title">合成完成</text>
      </view>

      <video
        class="result-video"
        :src="resultLocalPath || resultVideoUrl"
        controls
        :autoplay="false"
        webkit-playsinline
        playsinline
        x5-playsinline
        x5-video-player-type="h5"
        x5-video-player-fullscreen="false"
      />

      <view class="result-actions">
        <z-button type="success" text="💾 保存到相册" round @click="saveVideo" />
      </view>

      <!-- 视频后期编辑 -->
      <view class="edit-section">
        <text class="edit-title">视频后期编辑</text>

        <!-- 字幕 + AI优化标题 -->
        <view class="edit-row">
          <text class="edit-label">📝 字幕</text>
          <z-input v-model="subtitleText" placeholder="输入字幕文本（每行一句）" />
          <z-button size="xs" type="info" text="添加" @click="doEdit('subtitle')" :loading="editing" />
        </view>
        <view class="edit-row">
          <text class="edit-label">✨ AI优化</text>
          <z-input v-model="titleText" placeholder="标题（AI优化后自动填入）" />
          <z-button size="xs" type="purple" text="AI优化" @click="doAiOptimize" :loading="aiOptimizing" />
        </view>
        <view v-if="titleText" class="edit-row">
          <text class="edit-label"></text>
          <z-button size="xs" type="info" text="烧录标题+字幕" @click="doEdit('subtitle_with_title')" :loading="editing" />
          <text class="pip-name">标题将显示在视频顶部两行</text>
        </view>

        <!-- 画中画 -->
        <view class="edit-row">
          <text class="edit-label">🖼 画中画</text>
          <z-button size="sm" type="purple" text="📁 选择视频" round @click="choosePipVideo" />
          <z-button size="sm" type="info" text="🤖 AI生成" round @click="doAiPip" :loading="aiPipGenerating" />
        </view>
        <view v-if="pipVideoPath" class="edit-row">
          <text class="edit-label"></text>
          <text class="pip-name">{{ pipVideoName }}</text>
          <z-button size="xs" type="danger" text="✕" @click="pipVideoPath=''; pipVideoName=''" />
        </view>
        <view v-if="pipVideoPath" class="edit-row">
          <text class="edit-label">位置</text>
          <view class="pip-positions">
            <text
              v-for="pos in pipPositions" :key="pos.value"
              class="pip-pos-tag" :class="{ active: pipPosition === pos.value }"
              @tap="pipPosition = pos.value"
            >{{ pos.label }}</text>
          </view>
        </view>
        <view v-if="pipVideoPath" class="edit-row">
          <text class="edit-label">大小 {{ Math.round(pipScale * 100) }}%</text>
          <slider :value="pipScale * 100" :min="10" :max="80" :step="5" @change="e => pipScale = e.detail.value / 100" style="flex: 1;" />
          <z-button size="xs" type="info" text="合成PIP" @click="doEdit('pip')" :loading="editing" />
        </view>

        <!-- BGM -->
        <view class="edit-row">
          <text class="edit-label">🎵 BGM</text>
          <z-button size="sm" type="teal" text="选择BGM音频" round @click="chooseBgm" />
          <text v-if="bgmPath" class="pip-name">{{ bgmName }}</text>
          <z-button v-if="bgmPath" size="xs" type="teal" text="合成" @click="doEdit('bgm')" :loading="editing" />
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { isLoggedIn, getLicenseKey } from '@/utils/storage.js'
import { pickAudioFile, pickVideoFile, pickFile } from '@/utils/file-picker.js'
import {
  listAssets, uploadAsset, synthUploadAsset,
  gpuStatusCheck, gpuStatus, gpuPowerOn, waitForGpuOnline,
  heygemHealth, heygemSubmitByHash, heygemProgress, heygemDownloadUrl,
  videoEditUpload, videoEditDownloadUrl, uploadFileToPool,
  downloadFileWithAuth,
  aiOptimizeText
} from '@/utils/api.js'
import { on as wsOn, off as wsOff, send as wsSend } from '@/utils/websocket.js'

const ttsAudioUrl = ref('')
const ttsText = ref('')
const localAudioPath = ref('')
const localAudioName = ref('')
const recording = ref(false)
const recordSeconds = ref(0)

const avatars = ref([])
const avatarsLoading = ref(false)
const avatarUploading = ref(false)
const selectedAvatar = ref(null)

const synthesizing = ref(false)
const progressMsg = ref('')
const progressPct = ref(0)
const resultVideoUrl = ref('')
const resultLocalPath = ref('')

const subtitleText = ref('')
const titleText = ref('')
const pipVideoPath = ref('')
const pipVideoName = ref('')
const pipPosition = ref('bottom-right')
const pipScale = ref(0.3)
const bgmPath = ref('')
const bgmName = ref('')
const editing = ref(false)
const aiOptimizing = ref(false)
const aiPipGenerating = ref(false)

const pipPositions = [
  { value: 'top-left', label: '↖ 左上' },
  { value: 'top-right', label: '↗ 右上' },
  { value: 'bottom-left', label: '↙ 左下' },
  { value: 'bottom-right', label: '↘ 右下' },
]

// GPU 状态
const gpuOnlineStatus = ref('checking') // 'online', 'offline', 'checking'
const localStatusText = computed(() => {
  if (gpuOnlineStatus.value === 'online') return '就绪'
  if (gpuOnlineStatus.value === 'offline') return '未就绪'
  return '检测中...'
})

let recorderManager = null
let recordTimer = null
let audioCtx = null

const hasAudio = computed(() => !!(ttsAudioUrl.value || localAudioPath.value))

onMounted(() => {
  if (!isLoggedIn()) {
    uni.redirectTo({ url: '/pages/login/login' })
    return
  }

  // 恢复上次视频合成结果（刷新不丢失）
  const lastVideoUrl = uni.getStorageSync('heygem_last_video_url')
  const lastVideoLocal = uni.getStorageSync('heygem_last_video_local_path')
  if (lastVideoUrl && !resultVideoUrl.value) resultVideoUrl.value = lastVideoUrl
  if (lastVideoLocal && !resultLocalPath.value) resultLocalPath.value = lastVideoLocal

  loadAvatars()
  checkGpuStatus()
})

// 每次页面显示时读取 TTS 传递的音频（tab 页 onMounted 只执行一次）
onShow(() => {
  const url = uni.getStorageSync('tts_result_url')
  const txt = uni.getStorageSync('tts_result_text')
  if (url && url !== ttsAudioUrl.value) {
    ttsAudioUrl.value = url
    ttsText.value = txt || ''
  }
})

// 检查 GPU 状态（仅检查，不触发开机）
async function checkGpuStatus() {
  gpuOnlineStatus.value = 'checking'
  try {
    const res = await gpuStatusCheck()
    gpuOnlineStatus.value = (res.data && res.data.online) ? 'online' : 'offline'
    console.log('[GPU] 状态检查结果:', gpuOnlineStatus.value)
  } catch (e) {
    console.log('[GPU] 状态检查异常:', e.message)
    gpuOnlineStatus.value = 'offline'
  }
}

async function downloadAndCacheVideo(url) {
  // #ifdef H5
  // H5 平台不支持 saveFile / downloadFile 缓存，直接用原始 URL 播放
  resultLocalPath.value = ''
  return url
  // #endif

  // #ifndef H5
  uni.showLoading({ title: '准备视频...' })
  try {
    const dl = await new Promise((resolve, reject) => {
      uni.downloadFile({
        url,
        timeout: 180000,
        success: (r) => (r.statusCode === 200 && r.tempFilePath) ? resolve(r) : reject(new Error('下载失败')),
        fail: reject,
      })
    })

    try {
      const saved = await new Promise((resolve, reject) => {
        uni.saveFile({
          tempFilePath: dl.tempFilePath,
          success: resolve,
          fail: reject,
        })
      })
      resultLocalPath.value = saved.savedFilePath
      uni.setStorageSync('heygem_last_video_local_path', saved.savedFilePath)
      return saved.savedFilePath
    } catch (saveErr) {
      // saveFile 不可用时降级使用临时路径
      console.warn('[缓存] saveFile 失败，使用临时路径:', saveErr.errMsg || saveErr)
      resultLocalPath.value = dl.tempFilePath
      return dl.tempFilePath
    }
  } finally {
    uni.hideLoading()
  }
  // #endif
}

function clearTTSAudio() {
  ttsAudioUrl.value = ''; ttsText.value = ''
  uni.removeStorageSync('tts_result_url')
  uni.removeStorageSync('tts_result_text')
}

function goTTS() { uni.switchTab({ url: '/pages/tts/tts' }) }

function chooseAudio() {
  pickAudioFile().then(({ path, name }) => {
    localAudioPath.value = path
    localAudioName.value = name || '音频文件'
  }).catch(e => {
    if (e.message !== 'cancel') {
      uni.showToast({ title: e.message || '选择文件失败', icon: 'none' })
    }
  })
}

function startRecord() {
  recorderManager = uni.getRecorderManager()
  recordSeconds.value = 0
  recorderManager.onStart(() => {
    recording.value = true
    recordTimer = setInterval(() => { recordSeconds.value++ }, 1000)
  })
  recorderManager.onStop((res) => {
    recording.value = false; clearInterval(recordTimer)
    localAudioPath.value = res.tempFilePath
    localAudioName.value = `录音 ${recordSeconds.value}秒`
  })
  recorderManager.onError(() => { recording.value = false; clearInterval(recordTimer) })
  recorderManager.start({ format: 'wav', sampleRate: 16000 })
}

function stopRecord() { if (recorderManager) recorderManager.stop() }

function playLocalAudio() {
  if (audioCtx) { audioCtx.stop(); audioCtx.destroy() }
  audioCtx = uni.createInnerAudioContext()
  audioCtx.src = localAudioPath.value
  audioCtx.play()
}

async function loadAvatars() {
  avatarsLoading.value = true
  try {
    const res = await listAssets('avatar')
    if (res.code === 0 && Array.isArray(res.data)) {
      avatars.value = res.data
      if (avatars.value.length > 0 && !selectedAvatar.value) {
        selectedAvatar.value = avatars.value[0]
      }
    }
  } catch (e) { console.error('loadAvatars:', e) }
  finally { avatarsLoading.value = false }
}

async function uploadAvatar() {
  // 检查 GPU 状态，离线则先唤醒
  let needWake = false
  try {
    const st = await gpuStatus()
    needWake = !(st.data && st.data.online)
  } catch (e) { needWake = true }

  if (needWake) {
    avatarUploading.value = true
    uni.showLoading({ title: '加载本地程序...' })
    try {
      const waitRes = await waitForGpuOnline(180000, 5000)
      if (!waitRes.success) {
        uni.hideLoading()
        // GPU未上线，但后端会排队，继续上传
        console.log('[Upload] GPU未上线，上传将排队')
      }
    } catch (e) {
      console.log('[Upload] GPU唤醒异常:', e.message)
    }
    uni.hideLoading()
    avatarUploading.value = false
    gpuOnlineStatus.value = 'online'
    checkGpuStatus()
  }

  const doUpload = async (filePath, fileName) => {
    const name = fileName ? fileName.replace(/\.\w+$/, '') : '新数字人_' + Date.now()
    avatarUploading.value = true
    try {
      // 优先直连 GPU 上传（确保文件进入 GPU 文件池，合成时可直接使用）
      let upRes
      try {
        upRes = await synthUploadAsset(filePath, 'avatar', name)
        console.log('[数字人] 直连GPU上传成功:', upRes?.data?.file_hash)
      } catch (e) {
        console.log('[数字人] 直连GPU上传失败，走PHP:', e.message)
        upRes = await uploadAsset(filePath, 'avatar', name)
      }
      if (upRes.code === 0) {
        uni.showToast({ title: upRes.data?.queued ? '已排队，正在加载' : '上传成功', icon: 'success' })
        await loadAvatars()
      } else {
        const msg = upRes.msg || '上传失败'
        uni.showToast({ title: msg, icon: 'none' })
      }
    } catch (e) {
      let msg = e.message || '上传失败'
      if (msg.includes('413')) msg = '文件过大，请压缩后重试（建议<100MB）'
      uni.showModal({ title: '上传失败', content: msg, showCancel: false })
    } finally { avatarUploading.value = false }
  }

  // #ifdef H5 || APP-PLUS
  uni.chooseVideo({
    count: 1,
    sourceType: ['album'],
    success: (res) => doUpload(res.tempFilePath, '新数字人.mp4'),
  })
  // #endif

  // #ifdef MP-WEIXIN
  uni.chooseMessageFile({
    count: 1, type: 'file',
    extension: ['.mp4', '.mov', '.avi', '.mkv'],
    success: (res) => {
      if (!res.tempFiles?.length) return
      doUpload(res.tempFiles[0].path, res.tempFiles[0].name)
    },
  })
  // #endif
}

async function startSynthesis() {
  if (!hasAudio.value || !selectedAvatar.value) return

  synthesizing.value = true
  progressMsg.value = '初始化程序...'
  progressPct.value = 5
  resultVideoUrl.value = ''

  try {
    // === 步骤1: 检查 GPU 状态 ===
    let gpuOnline = false
    try {
      const statusRes = await gpuStatus()
      gpuOnline = !!(statusRes.data && statusRes.data.online)
      console.log('[合成] GPU 状态:', gpuOnline ? '在线' : '离线', statusRes)
    } catch (e) {
      console.log('[合成] GPU 状态检查异常:', e.message)
    }
    gpuOnlineStatus.value = gpuOnline ? 'online' : 'offline'

    if (!gpuOnline) {
      // GPU 离线，gpuStatus 已自动通过 health/proxy 触发开机通知
      progressMsg.value = '正在加载本地程序，预计两分钟...'
      progressPct.value = 8
      // 不在这里死等，继续流程，doUploadAudio 会在上传失败时自动等待GPU
      console.log('[合成] GPU离线，继续流程，上传时会自动等待')
    }

    // === 步骤2: 准备音频（先下载 TTS 音频再上传） ===
    progressMsg.value = '准备音频...'
    progressPct.value = 18

    const av = selectedAvatar.value
    let audioH = '', audioE = '.wav'

    // 上传音频的通用函数（优先直连GPU，失败走PHP代理）
    async function doUploadAudio(filePath, name) {
      // ① 优先尝试直连 GPU 上传（跨过PHP，避免PHP无法连接GPU的问题）
      try {
        const directRes = await synthUploadAsset(filePath, 'voice', name)
        console.log('[合成] 直连GPU上传返回:', JSON.stringify(directRes))
        if (directRes.code === 0 && directRes.data?.file_hash) {
          return directRes
        }
      } catch (e) {
        console.log('[合成] 直连GPU上传失败，走PHP代理:', e.message)
      }

      // ② 回退到 PHP 代理上传
      let upRes = await uploadAsset(filePath, 'voice', name)
      console.log('[合成] PHP代理上传返回:', JSON.stringify(upRes))
      if (upRes.code !== 0) throw new Error(upRes.msg || '音频上传失败')

      // GPU 离线时后端返回 queued=true 但没有 file_hash
      // 需要等 GPU 上线后重新上传才能拿到 hash
      if (upRes.data?.queued && !upRes.data?.file_hash) {
        progressMsg.value = '正在加载本地程序，预计两分钟...'
        progressPct.value = 12

        const maxWait = 300000
        const pollInterval = 5000
        const startT = Date.now()
        let gpuReady = false
        while (Date.now() - startT < maxWait) {
          const elapsed = Math.round((Date.now() - startT) / 1000)
          progressMsg.value = `正在加载本地程序... ${elapsed}s（预计两分钟）`
          progressPct.value = Math.min(18, 12 + Math.round(6 * elapsed / 180))
          try {
            const st = await gpuStatus()
            if (st.data && st.data.online) { gpuReady = true; break }
          } catch (e) { /* continue */ }
          await sleep(pollInterval)
        }

        if (!gpuReady) {
          throw new Error('程序加载超时，请稍后重试')
        }

        gpuOnlineStatus.value = 'online'
        progressMsg.value = '程序已就绪，上传音频...'
        progressPct.value = 20
        // GPU 上线→直连上传（不再走PHP）
        try {
          upRes = await synthUploadAsset(filePath, 'voice', name)
        } catch (e2) {
          upRes = await uploadAsset(filePath, 'voice', name)
        }
        console.log('[合成] 重新上传返回:', JSON.stringify(upRes))
        if (upRes.code !== 0) throw new Error(upRes.msg || '音频上传失败')
      }
      return upRes
    }

    let audioFilePath = ''
    if (localAudioPath.value) {
      audioFilePath = localAudioPath.value
    } else if (ttsAudioUrl.value) {
      // TTS 音频必须先下载到本地（需要 sign 授权）
      progressMsg.value = '下载TTS音频...'
      let dlRes
      try {
        dlRes = await downloadFileWithAuth(ttsAudioUrl.value, 60000)
      } catch (e) {
        console.error('[合成] TTS音频下载失败:', e.message)
        throw new Error('TTS音频下载失败，请检查网络或重新合成音频')
      }
      if (!dlRes.tempFilePath) {
        throw new Error('TTS音频下载失败，未获取到文件')
      }
      audioFilePath = dlRes.tempFilePath
    }

    if (audioFilePath) {
      progressMsg.value = '上传音频...'
      const upRes = await doUploadAudio(audioFilePath, 'synth_audio_' + Date.now())
      audioH = upRes.data?.file_hash || ''
      audioE = upRes.data?.file_ext || '.wav'
    }

    if (!audioH) {
      console.error('[合成] 音频准备失败: hash为空, 上传可能返回了排队状态')
      throw new Error('音频上传未返回文件标识，请确保程序就绪后重试')
    }

    // === 步骤3: 提交合成任务 ===
    progressMsg.value = '提交合成任务...'
    progressPct.value = 25

    const submitRes = await heygemSubmitByHash(audioH, audioE, av.file_hash, av.file_ext)
    if (submitRes.code !== 0) throw new Error(submitRes.msg || '提交失败')

    const taskId = submitRes.data?.task_id
    if (!taskId) throw new Error('提交失败：未获取任务ID')

    // 如果任务是排队状态，显示提示
    if (submitRes.data?.status === 'queued') {
      progressMsg.value = '正在加载本地程序，预计两分钟...'
      progressPct.value = 28
    }

    // === 步骤4: WS 实时推送 + HTTP 轮询兆底 ===
    let done = false
    let pollFailCount = 0
    let wsError = null  // WS 推送报错时存储错误信息

    // 注册 WS 进度监听（实时推送，更快更节省）
    const wsProgressHandler = (data) => {
      if (data.task_id !== taskId) return
      console.log('[合成] WS 推送:', data.status, data.progress)
      progressPct.value = data.progress || progressPct.value
      progressMsg.value = data.message || `合成中 ${data.progress || ''}%`

      if (data.status === 'done') {
        done = true
      } else if (data.status === 'error') {
        wsError = data.message || data.error || '合成失败'
      } else if (data.status === 'queued') {
        progressMsg.value = '任务排队中，正在加载本地程序...'
      }
    }
    wsOn('gpu.task.progress', wsProgressHandler)

    try {
      while (!done) {
        if (wsError) throw new Error(wsError)

        // HTTP 轮询作为兆底（8s 间隔，WS 推送是主要更新源）
        await sleep(8000)
        if (done || wsError) break  // WS 可能在 sleep 期间推送了结果

        try {
          const pRes = await heygemProgress(taskId)
          pollFailCount = 0

          if (pRes.code === 0 && pRes.data) {
            const d = pRes.data
            progressPct.value = d.progress || progressPct.value
            progressMsg.value = d.message || `合成中 ${d.progress || ''}%`

            if (d.status === 'done') {
              done = true
            } else if (d.status === 'error') {
              throw new Error(d.error || '合成失败')
            } else if (d.status === 'queued') {
              progressMsg.value = '任务排队中，正在加载本地程序...'
            }
          }
        } catch (pollErr) {
          if (wsError) throw new Error(wsError)  // WS 报错优先
          pollFailCount++
          console.log('[合成] 进度查询失败:', pollErr.message, '连续失败:', pollFailCount)
          if (pollFailCount >= 10) {
            throw new Error('进度查询失败超过10次，请稍后重试')
          }
          await sleep(5000)
        }
      }
    } finally {
      wsOff('gpu.task.progress', wsProgressHandler)
    }

    if (wsError) throw new Error(wsError)

    // done 后下载视频
    resultVideoUrl.value = heygemDownloadUrl(taskId)
    uni.setStorageSync('heygem_last_video_url', resultVideoUrl.value)
    try {
      await downloadAndCacheVideo(resultVideoUrl.value)
    } catch (e) {
      console.error('缓存视频失败:', e)
    }

    progressPct.value = 100
    progressMsg.value = '合成完成！'
    checkGpuStatus() // 刷新GPU状态
    uni.showToast({ title: '视频合成完成', icon: 'success' })
    setTimeout(() => { progressMsg.value = '' }, 2000)

  } catch (e) {
    uni.showModal({ title: '合成失败', content: e.message || '未知错误', showCancel: false })
    progressMsg.value = ''
    progressPct.value = 0
  } finally {
    synthesizing.value = false
  }
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)) }

function saveVideo() {
  if (!resultVideoUrl.value && !resultLocalPath.value) return

  const doSave = (path) => {
    uni.saveVideoToPhotosAlbum({
      filePath: path,
      success() { uni.showToast({ title: '已保存到相册', icon: 'success' }) },
      fail() { uni.showToast({ title: '保存失败', icon: 'none' }) },
    })
  }

  if (resultLocalPath.value) {
    doSave(resultLocalPath.value)
    return
  }

  downloadAndCacheVideo(resultVideoUrl.value)
    .then((p) => doSave(p))
    .catch(() => uni.showToast({ title: '下载失败', icon: 'none' }))
}

function choosePipVideo() {
  pickVideoFile().then(({ path, name }) => {
    pipVideoPath.value = path
    pipVideoName.value = name || 'PIP视频'
  }).catch(e => {
    if (e.message !== 'cancel') {
      uni.showToast({ title: e.message || '选择视频失败', icon: 'none' })
    }
  })
}

function chooseBgm() {
  pickAudioFile().then(({ path, name }) => {
    bgmPath.value = path
    bgmName.value = name || 'BGM'
  }).catch(e => {
    if (e.message !== 'cancel') {
      uni.showToast({ title: e.message || '选择音频失败', icon: 'none' })
    }
  })
}

// AI 优化标题
async function doAiOptimize() {
  const text = subtitleText.value.trim()
  if (!text) {
    uni.showToast({ title: '请先输入字幕文本', icon: 'none' })
    return
  }
  aiOptimizing.value = true
  try {
    const res = await aiOptimizeText(text)
    if (res.code === 0 && res.data) {
      // AI返回优化后的标题和正文
      titleText.value = res.data.title || ''
      if (res.data.subtitle_text || res.data.text) {
        subtitleText.value = res.data.subtitle_text || res.data.text || ''
      }
      uni.showToast({ title: 'AI优化完成', icon: 'success' })
    } else {
      throw new Error(res.msg || 'AI优化失败')
    }
  } catch (e) {
    uni.showToast({ title: e.message || 'AI优化失败', icon: 'none' })
  } finally {
    aiOptimizing.value = false
  }
}

// AI 画中画生成
function doAiPip() {
  const text = subtitleText.value.trim() || ttsText.value.trim()
  if (!text) {
    uni.showToast({ title: '请先输入文案或字幕', icon: 'none' })
    return
  }
  aiPipGenerating.value = true
  const requestId = `pip_ai_${Date.now()}`

  // 监听结果
  const onResult = (data) => {
    if (data.request_id !== requestId) return
    wsOff('chatglm_video_result', onResult)
    aiPipGenerating.value = false

    if (data.error) {
      uni.showToast({ title: data.error_msg || 'AI生成失败', icon: 'none' })
      return
    }
    if (data.video_url) {
      pipVideoPath.value = data.video_url
      pipVideoName.value = 'AI生成视频'
      uni.showToast({ title: 'AI视频生成完成', icon: 'success' })
    }
  }
  wsOn('chatglm_video_result', onResult)

  // 发送请求
  const sent = wsSend({
    type: 'chatglm_video',
    content: text,
    request_id: requestId,
  })
  if (!sent) {
    wsOff('chatglm_video_result', onResult)
    aiPipGenerating.value = false
    uni.showToast({ title: 'WebSocket未连接', icon: 'none' })
  }
}

async function doEdit(editType) {
  if (!resultVideoUrl.value && !resultLocalPath.value) {
    uni.showToast({ title: '请先合成视频', icon: 'none' })
    return
  }

  editing.value = true
  try {
    // 先下载合成结果到本地（如果还没下载）
    let videoPath = resultLocalPath.value
    if (!videoPath) {
      videoPath = await downloadAndCacheVideo(resultVideoUrl.value)
    }

    const formData = {}
    if (editType === 'subtitle') {
      if (!subtitleText.value.trim()) {
        uni.showToast({ title: '请输入字幕', icon: 'none' })
        editing.value = false
        return
      }
      formData.subtitle_text = subtitleText.value.trim()
    } else if (editType === 'subtitle_with_title') {
      formData.subtitle_text = subtitleText.value.trim()
      formData.title_text = titleText.value.trim()
      editType = 'subtitle' // GPU 端统一用 subtitle
    } else if (editType === 'pip') {
      formData.pip_position = pipPosition.value
      formData.pip_scale = String(pipScale.value)
      // PIP 视频需要先上传到 GPU 文件池
      if (pipVideoPath.value) {
        const isUrl = pipVideoPath.value.startsWith('http')
        if (!isUrl) {
          uni.showLoading({ title: '上传画中画视频...' })
          try {
            const uploadRes = await uploadFileToPool(pipVideoPath.value)
            if (uploadRes.code === 0 && uploadRes.data?.hash) {
              formData.pip_video_hash = uploadRes.data.hash
            }
          } catch (upErr) {
            console.error('[PIP] 上传PIP视频失败:', upErr)
            throw new Error('PIP视频上传失败: ' + upErr.message)
          }
        } else {
          // AI 生成的视频已在 GPU 上，传 URL
          formData.pip_video_url = pipVideoPath.value
        }
      }
    }

    uni.showLoading({ title: '视频编辑中...' })

    const res = await videoEditUpload(videoPath, editType, formData)
    if (res.code === 0 && res.data) {
      resultVideoUrl.value = videoEditDownloadUrl(res.data.task_id)
      resultLocalPath.value = '' // 需要重新下载
      uni.showToast({ title: '编辑完成', icon: 'success' })
    } else {
      throw new Error(res.msg || '编辑失败')
    }
  } catch (e) {
    uni.showModal({ title: '编辑失败', content: e.message, showCancel: false })
  } finally {
    editing.value = false
    uni.hideLoading()
  }
}
</script>

<style lang="scss" scoped>
.synth-page {
  min-height: 100vh;
  background: #f1f4fa;
  padding: 20rpx 30rpx 140rpx;
}

.card {
  background: #fff;
  border-radius: 20rpx;
  padding: 30rpx;
  margin-bottom: 24rpx;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.04);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 20rpx;
}

.step-badge {
  width: 44rpx; height: 44rpx; border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff; font-size: 24rpx; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}

.card-icon { font-size: 36rpx; }
.card-title { font-size: 30rpx; font-weight: 600; color: #1e293b; flex: 1; }

.audio-ready {
  display: flex; align-items: center; gap: 16rpx;
  padding: 20rpx; background: #f0fdf4; border-radius: 12rpx; border: 2rpx solid #bbf7d0;
}

.ready-icon { font-size: 36rpx; }
.ready-info { flex: 1; }
.ready-title { font-size: 26rpx; font-weight: 600; color: #15803d; display: block; }
.ready-desc { font-size: 22rpx; color: #4ade80; display: block; margin-top: 4rpx; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 360rpx; }

.audio-options { display: flex; gap: 16rpx; flex-wrap: wrap; }

.recording-bar {
  display: flex; align-items: center; gap: 12rpx; margin-top: 16rpx;
  padding: 16rpx 20rpx; background: #fee2e2; border-radius: 12rpx;
}
.rec-dot { font-size: 24rpx; animation: blink 1s infinite; }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }
.rec-text { flex: 1; font-size: 24rpx; color: #b91c1c; }

.avatar-scroll { white-space: nowrap; }
.avatar-list { display: flex; gap: 20rpx; padding: 4rpx 0; }

.avatar-item {
  display: inline-flex; flex-direction: column; align-items: center;
  padding: 16rpx 20rpx; background: #f8fafc; border-radius: 16rpx;
  border: 2rpx solid #e2e8f0; min-width: 120rpx; flex-shrink: 0;
  &.active { background: #eef2ff; border-color: #6366f1; }
}

.avatar-thumb {
  width: 80rpx; height: 80rpx; border-radius: 50%;
  background: linear-gradient(135deg, #c7d2fe, #e0e7ff);
  display: flex; align-items: center; justify-content: center; margin-bottom: 8rpx;
}

.avatar-emoji { font-size: 40rpx; }
.avatar-name { font-size: 22rpx; color: #334155; max-width: 120rpx; overflow: hidden; text-overflow: ellipsis; }
.avatar-days { font-size: 18rpx; color: #94a3b8; margin-top: 2rpx; }

.loading-row, .empty-row { padding: 30rpx 0; text-align: center; }
.loading-text, .empty-text { font-size: 24rpx; color: #94a3b8; }

.upload-bar { margin-top: 16rpx; padding: 16rpx; background: #dbeafe; border-radius: 12rpx; }
.upload-text { font-size: 24rpx; color: #1d4ed8; }

// GPU 状态指示器
.gpu-status {
  display: flex; align-items: center; gap: 8rpx;
  padding: 8rpx 16rpx; border-radius: 20rpx; font-size: 20rpx;
  &.online { background: #dcfce7; }
  &.offline { background: #fee2e2; }
  &.checking { background: #fef3c7; }
}
.gpu-dot {
  width: 12rpx; height: 12rpx; border-radius: 50%;
  .online & { background: #22c55e; }
  .offline & { background: #ef4444; }
  .checking & { background: #f59e0b; animation: blink 1s infinite; }
}
.gpu-text {
  .online & { color: #15803d; }
  .offline & { color: #b91c1c; }
  .checking & { color: #92400e; }
}
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }

.gpu-offline-tip {
  display: flex; align-items: flex-start; gap: 12rpx;
  padding: 16rpx 20rpx; margin-bottom: 16rpx;
  background: #fffbeb; border: 2rpx solid #fde68a; border-radius: 12rpx;
}
.tip-icon { font-size: 28rpx; flex-shrink: 0; }
.tip-text { font-size: 22rpx; color: #92400e; line-height: 1.5; }

.progress-info {
  margin-top: 20rpx; background: #f1f5f9; border-radius: 12rpx;
  overflow: hidden; position: relative; height: 48rpx;
}
.progress-bar-inner {
  position: absolute; left: 0; top: 0; bottom: 0;
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
  border-radius: 12rpx; transition: width 0.5s ease;
}
.progress-label {
  position: relative; z-index: 1; font-size: 22rpx; color: #334155;
  line-height: 48rpx; padding-left: 16rpx;
}

.result-card { border: 2rpx solid #bbf7d0; background: #f0fdf4; }
.result-video { width: 100%; border-radius: 12rpx; margin-bottom: 20rpx; }
.result-actions { display: flex; gap: 16rpx; flex-wrap: wrap; margin-bottom: 20rpx; }

.edit-section {
  padding-top: 20rpx; border-top: 2rpx solid #dcfce7;
}
.edit-title { font-size: 28rpx; font-weight: 600; color: #1e293b; margin-bottom: 16rpx; display: block; }
.edit-row {
  display: flex; align-items: center; gap: 12rpx; margin-bottom: 16rpx; flex-wrap: wrap;
}
.edit-label { font-size: 24rpx; color: #334155; font-weight: 500; min-width: 100rpx; }
.pip-name { font-size: 20rpx; color: #64748b; max-width: 200rpx; overflow: hidden; text-overflow: ellipsis; }

.pip-positions { display: flex; gap: 8rpx; flex-wrap: wrap; }
.pip-pos-tag {
  padding: 6rpx 16rpx; border-radius: 8rpx; font-size: 20rpx;
  background: #f1f5f9; color: #64748b; border: 2rpx solid #e2e8f0;
  &.active { background: #eef2ff; color: #6366f1; border-color: #6366f1; font-weight: 600; }
}
</style>
