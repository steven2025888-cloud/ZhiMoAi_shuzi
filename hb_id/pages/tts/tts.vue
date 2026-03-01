<template>
  <view class="tts-page">
    <!-- 输入区域 -->
    <view class="card">
      <view class="card-header">
        <text class="card-icon">📝</text>
        <text class="card-title">输入文本</text>
      </view>
      <textarea
        class="text-area"
        v-model="inputText"
        placeholder="请输入要合成语音的文字..."
        :maxlength="5000"
        :auto-height="false"
      />
      <view class="text-count">
        <text class="count-text">{{ inputText.length }} / 5000</text>
      </view>
    </view>

    <!-- 音色选择 -->
    <view class="card">
      <view class="card-header">
        <text class="card-icon">🎙️</text>
        <text class="card-title">选择音色</text>
        <z-button size="xs" type="light" text="📝 记录" @click="goToHistory" />
        <z-button size="xs" type="light" text="刷新" @click="loadVoices" style="margin-left: 12rpx;" />
        <z-button size="xs" type="primary" text="+ 上传" @click="uploadVoice" style="margin-left: 12rpx;" />
      </view>

      <view v-if="voicesLoading" class="loading-row">
        <text class="loading-text">加载音色列表...</text>
      </view>

      <scroll-view v-else-if="voices.length > 0" scroll-x class="voice-scroll" :show-scrollbar="false">
        <view class="voice-list">
          <view
            v-for="voice in voices"
            :key="voice.id"
            class="voice-item"
            :class="{ active: selectedVoice?.id === voice.id }"
            @tap="selectedVoice = voice"
          >
            <text class="voice-name">{{ voice.name }}</text>
            <text v-if="voice.is_default" class="voice-tag">默认</text>
          </view>
        </view>
      </scroll-view>

      <view v-if="!voicesLoading && voices.length === 0" class="empty-row">
        <text class="empty-text">暂无音色，请点击"上传"添加</text>
      </view>

      <view v-if="uploading" class="upload-bar">
        <text class="upload-text">上传中...</text>
      </view>
    </view>

    <!-- 合成按钮 -->
    <view class="action-area">
      <z-button
        type="primary"
        size="lg"
        :text="synthesizing ? '合成中...' : '🎵 开始合成'"
        :loading="synthesizing"
        :disabled="synthesizing || !inputText.trim() || !selectedVoice"
        block
        round
        @click="startSynthesize"
      />
    </view>

    <!-- 合成结果 -->
    <view v-if="resultUrl" class="card result-card">
      <view class="card-header">
        <text class="card-icon">✅</text>
        <text class="card-title">合成完成</text>
      </view>

      <view class="result-actions">
        <z-button type="success" text="▶ 播放" round @click="playAudio" />
        <z-button type="info" text="💾 保存" round @click="downloadAudio" />
        <z-button type="purple" text="➡️ 用于视频合成" round @click="useForVideo" />
      </view>

      <view v-if="playing" class="playing-bar">
        <text class="playing-text">🔊 正在播放...</text>
        <z-button size="xs" type="danger" text="停止" @click="stopAudio" />
      </view>
    </view>

    <!-- 进度提示 -->
    <view v-if="progressMsg" class="progress-bar">
      <text class="progress-text">{{ progressMsg }}</text>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  listVoiceModels,
  ttsCreate, ttsResult, ttsDownloadUrl,
  downloadFileWithAuth,
} from '@/utils/api.js'
import { isLoggedIn } from '@/utils/storage.js'

const inputText = ref('')
const voices = ref([])
const selectedVoice = ref(null)
const voicesLoading = ref(false)
const uploading = ref(false)
const synthesizing = ref(false)
const progressMsg = ref('')
const resultUrl = ref('')
const resultTaskId = ref('')
const resultTempAudioPath = ref('')
const playing = ref(false)

let audioCtx = null

onMounted(() => {
  if (!isLoggedIn()) {
    uni.redirectTo({ url: '/pages/login/login' })
    return
  }
  // 恢复上次合成结果（刷新页面不丢失，直到新合成覆盖）
  const lastUrl = uni.getStorageSync('tts_last_result_url')
  const lastTaskId = uni.getStorageSync('tts_last_result_task_id')
  if (lastUrl && !resultUrl.value) {
    resultUrl.value = lastUrl
    resultTaskId.value = lastTaskId || ''
  }
  loadVoices()
})

async function loadVoices() {
  voicesLoading.value = true
  try {
    const res = await listVoiceModels()
    if (res.code === 0 && Array.isArray(res.data)) {
      voices.value = res.data
      if (voices.value.length > 0 && !selectedVoice.value) {
        selectedVoice.value = voices.value[0]
      }
    }
  } catch (e) {
    console.error('加载音色失败:', e)
    uni.showToast({ title: '加载音色失败', icon: 'none' })
  } finally {
    voicesLoading.value = false
  }
}

function uploadVoice() {
  // 使用 uni.chooseFile 替代 chooseMessageFile，兼容 H5/App
  // #ifdef H5 || APP-PLUS
  uni.chooseFile({
    count: 1,
    extension: ['.wav', '.mp3', '.m4a', '.aac', '.flac'],
    success: async (res) => {
      if (!res.tempFilePaths || !res.tempFilePaths.length) return
      const filePath = res.tempFilePaths[0]
      const fileName = res.tempFiles && res.tempFiles[0] ? res.tempFiles[0].name : '新音色'
      const name = fileName.replace(/\.\w+$/, '')

      uploading.value = true
      try {
        const upRes = await uploadVoiceModel(filePath, name)
        if (upRes.code === 0) {
          uni.showToast({ title: '上传成功', icon: 'success' })
          await loadVoices()
        } else {
          uni.showToast({ title: upRes.msg || '上传失败', icon: 'none' })
        }
      } catch (e) {
        uni.showModal({ title: '上传失败', content: e.message || '网络错误', showCancel: false })
      } finally {
        uploading.value = false
      }
    },
  })
  // #endif

  // #ifdef MP-WEIXIN
  uni.chooseMessageFile({
    count: 1,
    type: 'file',
    extension: ['.wav', '.mp3', '.m4a', '.aac', '.flac'],
    success: async (res) => {
      if (!res.tempFiles || !res.tempFiles.length) return
      const file = res.tempFiles[0]
      const name = file.name ? file.name.replace(/\.\w+$/, '') : '新音色'

      uploading.value = true
      try {
        const upRes = await uploadVoiceModel(file.path, name)
        if (upRes.code === 0) {
          uni.showToast({ title: '上传成功', icon: 'success' })
          await loadVoices()
        } else {
          uni.showToast({ title: upRes.msg || '上传失败', icon: 'none' })
        }
      } catch (e) {
        uni.showModal({ title: '上传失败', content: e.message || '网络错误', showCancel: false })
      } finally {
        uploading.value = false
      }
    },
  })
  // #endif
}

async function startSynthesize() {
  if (!inputText.value.trim()) {
    uni.showToast({ title: '请输入文本', icon: 'none' })
    return
  }
  if (!selectedVoice.value) {
    uni.showToast({ title: '请选择音色', icon: 'none' })
    return
  }

  synthesizing.value = true
  progressMsg.value = '提交合成任务...'
  // 不清空已有结果：刷新/等待期间保持显示，直到新结果覆盖

  try {
    const createRes = await ttsCreate(inputText.value.trim(), selectedVoice.value.id)
    if (createRes.code !== 0) {
      throw new Error(createRes.msg || '创建任务失败')
    }

    const taskId = createRes.data?.taskId
    const voiceUrl = createRes.data?.voiceUrl

    if (voiceUrl) {
      resultUrl.value = ttsDownloadUrl(voiceUrl)
      resultTaskId.value = taskId
      resultTempAudioPath.value = ''
      uni.setStorageSync('tts_last_result_url', resultUrl.value)
      uni.setStorageSync('tts_last_result_task_id', resultTaskId.value)
      progressMsg.value = ''
      uni.showToast({ title: '合成完成', icon: 'success' })
      return
    }

    if (!taskId) throw new Error('未返回 taskId')

    progressMsg.value = '合成中，请稍候...'
    let retries = 0
    const maxRetries = 60

    while (retries < maxRetries) {
      await sleep(2000)
      retries++

      const resultRes = await ttsResult(taskId)
      if (resultRes.code === 0 && resultRes.data) {
        const d = resultRes.data
        if (d.voiceUrl || d.voice_url) {
          const url = d.voiceUrl || d.voice_url
          resultUrl.value = ttsDownloadUrl(url)
          resultTaskId.value = taskId
          resultTempAudioPath.value = ''
          uni.setStorageSync('tts_last_result_url', resultUrl.value)
          uni.setStorageSync('tts_last_result_task_id', resultTaskId.value)
          progressMsg.value = ''
          uni.showToast({ title: '合成完成', icon: 'success' })
          return
        }
        if (d.status === 'failed' || d.status === 'error') {
          throw new Error(d.msg || '合成失败')
        }
      }
      progressMsg.value = `合成中... (${retries}/${maxRetries})`
    }

    throw new Error('合成超时，请重试')
  } catch (e) {
    uni.showModal({ title: '合成失败', content: e.message || '未知错误', showCancel: false })
    progressMsg.value = ''
  } finally {
    synthesizing.value = false
  }
}

function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)) }

function goToHistory() {
  uni.navigateTo({ url: '/pages/tts/history' })
}

function playAudio() {
  if (!resultUrl.value) return

  const startPlay = (src) => {
    stopAudio()
    audioCtx = uni.createInnerAudioContext()
    audioCtx.src = src
    audioCtx.onPlay(() => { playing.value = true })
    audioCtx.onEnded(() => { playing.value = false })
    audioCtx.onError(() => { playing.value = false })
    audioCtx.play()
  }

  // 直链在部分端上会无声：先下载到本地临时文件再播放
  if (resultTempAudioPath.value) {
    startPlay(resultTempAudioPath.value)
    return
  }

  uni.showLoading({ title: '下载音频...' })
  downloadFileWithAuth(resultUrl.value, 60000)
    .then((res) => {
      uni.hideLoading()
      resultTempAudioPath.value = res.tempFilePath
      startPlay(res.tempFilePath)
    })
    .catch(() => {
      uni.hideLoading()
      uni.showToast({ title: '下载失败', icon: 'none' })
    })
}

function stopAudio() {
  if (audioCtx) { audioCtx.stop(); audioCtx.destroy(); audioCtx = null }
  playing.value = false
}

function downloadAudio() {
  if (!resultUrl.value) return
  uni.showLoading({ title: '下载中...' })
  downloadFileWithAuth(resultUrl.value, 60000)
    .then((res) => {
      uni.saveFile({
        tempFilePath: res.tempFilePath,
        success() { uni.hideLoading(); uni.showToast({ title: '保存成功', icon: 'success' }) },
        fail() { uni.hideLoading(); uni.showToast({ title: '保存失败', icon: 'none' }) },
      })
    })
    .catch(() => {
      uni.hideLoading()
      uni.showToast({ title: '下载失败', icon: 'none' })
    })
}

function useForVideo() {
  uni.setStorageSync('tts_result_url', resultUrl.value)
  uni.setStorageSync('tts_result_text', inputText.value.trim())
  uni.switchTab({ url: '/pages/synthesis/synthesis' })
  uni.showToast({ title: '已传递到视频合成', icon: 'success' })
}
</script>

<style lang="scss" scoped>
.tts-page {
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

.card-icon { font-size: 36rpx; }

.card-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #1e293b;
  flex: 1;
}

.text-area {
  width: 100%;
  min-height: 200rpx;
  padding: 20rpx;
  font-size: 28rpx;
  color: #334155;
  background: #f8fafc;
  border-radius: 12rpx;
  border: 2rpx solid #e2e8f0;
  box-sizing: border-box;
}

.text-count {
  text-align: right;
  margin-top: 8rpx;
}

.count-text {
  font-size: 22rpx;
  color: #94a3b8;
}

.voice-scroll {
  white-space: nowrap;
}

.voice-list {
  display: flex;
  gap: 16rpx;
  padding: 4rpx 0;
}

.voice-item {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  padding: 20rpx 28rpx;
  background: #f8fafc;
  border-radius: 16rpx;
  border: 2rpx solid #e2e8f0;
  min-width: 140rpx;
  flex-shrink: 0;

  &.active {
    background: #eef2ff;
    border-color: #6366f1;
  }
}

.voice-name {
  font-size: 24rpx;
  font-weight: 600;
  color: #334155;
  max-width: 160rpx;
  overflow: hidden;
  text-overflow: ellipsis;
}

.voice-tag {
  font-size: 20rpx;
  color: #94a3b8;
  margin-top: 4rpx;
}

.loading-row, .empty-row {
  padding: 30rpx 0;
  text-align: center;
}

.loading-text, .empty-text {
  font-size: 24rpx;
  color: #94a3b8;
}

.action-area {
  margin: 10rpx 0 24rpx;
}

.result-card {
  border: 2rpx solid #bbf7d0;
  background: #f0fdf4;
}

.result-actions {
  display: flex;
  gap: 16rpx;
  flex-wrap: wrap;
}

.playing-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 20rpx;
  padding: 16rpx 20rpx;
  background: #dbeafe;
  border-radius: 12rpx;
}

.playing-text {
  font-size: 24rpx;
  color: #1d4ed8;
}

.progress-bar {
  position: fixed;
  bottom: 120rpx;
  left: 30rpx;
  right: 30rpx;
  padding: 20rpx 30rpx;
  background: #1e293b;
  border-radius: 16rpx;
  z-index: 100;
}

.progress-text {
  font-size: 24rpx;
  color: #e2e8f0;
}
</style>
