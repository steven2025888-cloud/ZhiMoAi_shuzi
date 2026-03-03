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
          <text class="gpu-text">{{ gpuStatusText }}</text>
        </view>
      </view>

      <!-- GPU 离线提示 -->
      <view v-if="gpuOnlineStatus === 'offline'" class="gpu-offline-tip">
        <text class="tip-icon">💡</text>
        <text class="tip-text">GPU 服务器未运行，点击合成将自动唤醒（约1-3分钟）</text>
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

      <video class="result-video" :src="resultLocalPath || resultVideoUrl" controls :autoplay="false" />

      <view class="result-actions">
        <z-button type="success" text="💾 保存到相册" round @click="saveVideo" />
      </view>

      <!-- 视频后期编辑 -->
      <view class="edit-section">
        <text class="edit-title">视频后期编辑</text>

        <view class="edit-row">
          <text class="edit-label">📝 字幕</text>
          <z-input v-model="subtitleText" placeholder="输入字幕文本（每行一句）" />
          <z-button size="xs" type="info" text="添加" @click="doEdit('subtitle')" :loading="editing" />
        </view>

        <view class="edit-row">
          <text class="edit-label">🖼 画中画</text>
          <z-button size="sm" type="purple" text="选择画中画视频" round @click="choosePipVideo" />
          <text v-if="pipVideoPath" class="pip-name">{{ pipVideoName }}</text>
          <z-button v-if="pipVideoPath" size="xs" type="info" text="合成" @click="doEdit('pip')" :loading="editing" />
        </view>

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
import { isLoggedIn } from '@/utils/storage.js'
import {
  listAssets, uploadAsset,
  gpuStatus, gpuPowerOn, waitForGpuOnline,
  heygemHealth, heygemSubmitByHash, heygemProgress, heygemDownloadUrl,
  videoEditUpload, videoEditDownloadUrl,
  downloadFileWithAuth
} from '@/utils/api.js'

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
const pipVideoPath = ref('')
const pipVideoName = ref('')
const bgmPath = ref('')
const bgmName = ref('')
const editing = ref(false)

// GPU 状态
const gpuOnlineStatus = ref('checking') // 'online', 'offline', 'checking'
const gpuStatusText = computed(() => {
  if (gpuOnlineStatus.value === 'online') return 'GPU在线'
  if (gpuOnlineStatus.value === 'offline') return 'GPU离线'
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

  const url = uni.getStorageSync('tts_result_url')
  const txt = uni.getStorageSync('tts_result_text')
  if (url) { ttsAudioUrl.value = url; ttsText.value = txt || '' }

  // 恢复上次视频合成结果（刷新不丢失）
  const lastVideoUrl = uni.getStorageSync('heygem_last_video_url')
  const lastVideoLocal = uni.getStorageSync('heygem_last_video_local_path')
  if (lastVideoUrl && !resultVideoUrl.value) resultVideoUrl.value = lastVideoUrl
  if (lastVideoLocal && !resultLocalPath.value) resultLocalPath.value = lastVideoLocal

  loadAvatars()
  checkGpuStatus()
})

// 检查 GPU 状态
async function checkGpuStatus() {
  gpuOnlineStatus.value = 'checking'
  try {
    const res = await gpuStatus()
    gpuOnlineStatus.value = (res.code === 0 && res.data && res.data.online) ? 'online' : 'offline'
  } catch (e) {
    gpuOnlineStatus.value = 'offline'
  }
}

async function downloadAndCacheVideo(url) {
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
  } finally {
    uni.hideLoading()
  }
}

function clearTTSAudio() {
  ttsAudioUrl.value = ''; ttsText.value = ''
  uni.removeStorageSync('tts_result_url')
  uni.removeStorageSync('tts_result_text')
}

function goTTS() { uni.switchTab({ url: '/pages/tts/tts' }) }

function chooseAudio() {
  // #ifdef H5 || APP-PLUS
  uni.chooseFile({
    count: 1,
    extension: ['.wav', '.mp3', '.m4a', '.aac', '.flac'],
    success(res) {
      if (res.tempFilePaths?.length) {
        localAudioPath.value = res.tempFilePaths[0]
        localAudioName.value = res.tempFiles?.[0]?.name || '音频文件'
      }
    },
  })
  // #endif

  // #ifdef MP-WEIXIN
  uni.chooseMessageFile({
    count: 1, type: 'file',
    extension: ['.wav', '.mp3', '.m4a', '.aac', '.flac'],
    success(res) {
      if (res.tempFiles?.length) {
        localAudioPath.value = res.tempFiles[0].path
        localAudioName.value = res.tempFiles[0].name || '音频文件'
      }
    },
  })
  // #endif
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

function uploadAvatar() {
  // #ifdef H5 || APP-PLUS
  uni.chooseVideo({
    count: 1,
    sourceType: ['album'],
    success: async (res) => {
      const file = { path: res.tempFilePath, name: '新数字人.mp4' }
      const name = '新数字人_' + Date.now()

      avatarUploading.value = true
      try {
        const upRes = await uploadAsset(file.path, 'avatar', name)
        if (upRes.code === 0) {
          uni.showToast({ title: '上传成功', icon: 'success' })
          await loadAvatars()
        } else {
          uni.showToast({ title: upRes.msg || '上传失败', icon: 'none' })
        }
      } catch (e) {
        uni.showModal({ title: '上传失败', content: e.message, showCancel: false })
      } finally { avatarUploading.value = false }
    },
  })
  // #endif

  // #ifdef MP-WEIXIN
  uni.chooseMessageFile({
    count: 1, type: 'file',
    extension: ['.mp4', '.mov', '.avi', '.mkv'],
    success: async (res) => {
      if (!res.tempFiles?.length) return
      const file = res.tempFiles[0]
      const name = file.name ? file.name.replace(/\.\w+$/, '') : '新数字人'

      avatarUploading.value = true
      try {
        const upRes = await uploadAsset(file.path, 'avatar', name)
        if (upRes.code === 0) {
          uni.showToast({ title: '上传成功', icon: 'success' })
          await loadAvatars()
        } else {
          uni.showToast({ title: upRes.msg || '上传失败', icon: 'none' })
        }
      } catch (e) {
        uni.showModal({ title: '上传失败', content: e.message, showCancel: false })
      } finally { avatarUploading.value = false }
    },
  })
  // #endif
}

async function startSynthesis() {
  if (!hasAudio.value || !selectedAvatar.value) return

  synthesizing.value = true
  progressMsg.value = '检查 GPU 状态...'
  progressPct.value = 5
  resultVideoUrl.value = ''

  try {
    // 检查 GPU 状态，如果离线则发送开机请求
    let gpuOnline = false
    try {
      const statusRes = await gpuStatus()
      gpuOnline = statusRes.code === 0 && statusRes.data && statusRes.data.online
      console.log('[合成] GPU 状态:', gpuOnline ? '在线' : '离线')
    } catch (e) {
      console.log('[合成] GPU 状态检查失败:', e.message)
    }

    if (!gpuOnline) {
      // GPU 离线，发送开机请求
      progressMsg.value = '正在唤醒 GPU 服务器...'
      progressPct.value = 8
      
      try {
        const powerRes = await gpuPowerOn()
        if (powerRes.code === 0) {
          progressMsg.value = 'GPU 开机中，请稍候（约1-3分钟）...'
          progressPct.value = 10
          
          // 轮询等待 GPU 上线（最长等待 3 分钟）
          const waitRes = await waitForGpuOnline(180000, 5000)
          if (!waitRes.success) {
            throw new Error('GPU 开机超时，请稍后重试')
          }
          progressMsg.value = 'GPU 已就绪'
          progressPct.value = 15
        } else {
          console.log('[合成] 开机请求返回:', powerRes)
          // 即使开机请求失败，也尝试继续（可能 GPU 正在启动中）
          progressMsg.value = '等待 GPU 就绪...'
          await waitForGpuOnline(60000, 5000)
        }
      } catch (e) {
        console.log('[合成] GPU 开机流程:', e.message)
        // 继续尝试合成，让后续的 health check 决定是否失败
      }
    }

    progressMsg.value = '检查合成服务器...'
    progressPct.value = 18
    
    const health = await heygemHealth()
    if (health.code !== 0) throw new Error('合成服务器不可用，请稍后重试')

    progressMsg.value = '提交合成任务...'
    progressPct.value = 15

    // 用已上传资产的 hash 提交合成
    const av = selectedAvatar.value
    const audioHash = av.file_hash // TODO: 需要音频hash
    // 暂时使用avatar的hash作为video，音频需要先上传
    // 实际流程：音频也需要先上传到合成服务器

    let audioH = '', audioE = '.wav'
    if (localAudioPath.value) {
      // 上传本地音频到合成服务器
      progressMsg.value = '上传音频...'
      const upRes = await uploadAsset(localAudioPath.value, 'voice', '合成音频_' + Date.now())
      if (upRes.code !== 0) throw new Error('音频上传失败')
      audioH = upRes.data.file_hash
      audioE = upRes.data.file_ext
    } else if (ttsAudioUrl.value) {
      // TTS音频已在服务器，需要下载后上传
      progressMsg.value = '准备TTS音频...'
      const dlRes = await downloadFileWithAuth(ttsAudioUrl.value, 60000)
      const upRes = await uploadAsset(dlRes.tempFilePath, 'voice', 'tts_audio_' + Date.now())
      if (upRes.code !== 0) throw new Error('TTS音频上传失败')
      audioH = upRes.data.file_hash
      audioE = upRes.data.file_ext
    }

    if (!audioH) {
      console.error('音频检查失败:', {
        localAudioPath: localAudioPath.value,
        ttsAudioUrl: ttsAudioUrl.value,
        hasAudio: hasAudio.value
      })
      throw new Error('无有效音频，请先上传音频或从语音合成页面选择音频')
    }

    progressMsg.value = '提交合成...'
    progressPct.value = 25

    const submitRes = await heygemSubmitByHash(audioH, audioE, av.file_hash, av.file_ext)
    if (submitRes.code !== 0) throw new Error(submitRes.msg || '提交失败')

    const taskId = submitRes.data.task_id

    // 轮询进度
    let done = false
    while (!done) {
      await sleep(3000)
      const pRes = await heygemProgress(taskId)
      if (pRes.code === 0 && pRes.data) {
        const d = pRes.data
        progressPct.value = d.progress || progressPct.value
        progressMsg.value = d.message || `合成中 ${d.progress}%`

        if (d.status === 'done') {
          resultVideoUrl.value = heygemDownloadUrl(taskId)
          uni.setStorageSync('heygem_last_video_url', resultVideoUrl.value)
          // 播放更稳：先下载成“本地文件”再播放
          try {
            await downloadAndCacheVideo(resultVideoUrl.value)
          } catch (e) {
            console.error('缓存视频失败:', e)
          }
          done = true
        } else if (d.status === 'error') {
          throw new Error(d.error || '合成失败')
        }
      }
    }

    progressPct.value = 100
    progressMsg.value = '合成完成！'
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
  uni.chooseMessageFile({
    count: 1, type: 'file', extension: ['.mp4', '.mov'],
    success(res) {
      if (res.tempFiles?.length) {
        pipVideoPath.value = res.tempFiles[0].path
        pipVideoName.value = res.tempFiles[0].name || 'PIP视频'
      }
    },
  })
}

function chooseBgm() {
  uni.chooseMessageFile({
    count: 1, type: 'file', extension: ['.mp3', '.wav', '.m4a', '.aac'],
    success(res) {
      if (res.tempFiles?.length) {
        bgmPath.value = res.tempFiles[0].path
        bgmName.value = res.tempFiles[0].name || 'BGM'
      }
    },
  })
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
</style>
