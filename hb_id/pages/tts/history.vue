<template>
  <view class="history-page">
    <!-- 顶部操作栏 -->
    <view class="action-bar">
      <z-button size="sm" type="primary" text="🎵 新建合成" @click="goToTts" />
      <z-button size="sm" type="light" text="🔄 刷新" @click="loadHistory" />
    </view>

    <!-- 加载中 -->
    <view v-if="loading && records.length === 0" class="loading-view">
      <text class="loading-text">加载中...</text>
    </view>

    <!-- 记录列表 -->
    <view v-else-if="records.length > 0" class="records-list">
      <view
        v-for="record in records"
        :key="record.id"
        class="record-card"
        @tap="selectRecord(record)"
      >
        <view class="record-header">
          <text class="record-id">#{{ record.id }}</text>
          <text :class="['record-status', record.status === 1 ? 'success' : 'error']">
            {{ record.status === 1 ? '✅ 成功' : '❌ 失败' }}
          </text>
        </view>

        <view class="record-info">
          <text class="record-label">字数：</text>
          <text class="record-value">{{ record.text_len }} 字</text>
        </view>

        <view class="record-info">
          <text class="record-label">时间：</text>
          <text class="record-value">{{ record.created_at }}</text>
        </view>

        <view v-if="record.error_msg" class="record-error">
          <text class="error-text">{{ record.error_msg }}</text>
        </view>

        <view v-if="record.status === 1 && record.voice_url" class="record-actions">
          <z-button size="xs" type="success" text="▶ 播放" @click.stop="playRecord(record)" />
          <z-button size="xs" type="info" text="💾 保存" @click.stop="downloadRecord(record)" />
          <z-button size="xs" type="purple" text="➡️ 用于视频" @click.stop="useForVideo(record)" />
        </view>
      </view>
    </view>

    <!-- 空状态 -->
    <view v-else class="empty-view">
      <text class="empty-icon">📝</text>
      <text class="empty-text">暂无合成记录</text>
      <z-button type="primary" text="立即合成" @click="goToTts" style="margin-top: 40rpx;" />
    </view>

    <!-- 分页 -->
    <view v-if="total > limit" class="pagination">
      <z-button
        size="sm"
        type="light"
        text="上一页"
        :disabled="page <= 1"
        @click="prevPage"
      />
      <text class="page-info">{{ page }} / {{ Math.ceil(total / limit) }}</text>
      <z-button
        size="sm"
        type="light"
        text="下一页"
        :disabled="page >= Math.ceil(total / limit)"
        @click="nextPage"
      />
    </view>

    <!-- 播放提示 -->
    <view v-if="playing" class="playing-toast">
      <text class="playing-text">🔊 正在播放...</text>
      <z-button size="xs" type="danger" text="停止" @click="stopAudio" />
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ttsHistory, ttsDownloadUrl, downloadFileWithAuth } from '@/utils/api.js'
import { isLoggedIn } from '@/utils/storage.js'

const records = ref([])
const loading = ref(false)
const page = ref(1)
const limit = ref(20)
const total = ref(0)
const playing = ref(false)
const playingRecordId = ref(null)
const playingTempPath = ref('')

let audioCtx = null

onMounted(() => {
  if (!isLoggedIn()) {
    uni.redirectTo({ url: '/pages/login/login' })
    return
  }
  loadHistory()
})

async function loadHistory() {
  loading.value = true
  try {
    const res = await ttsHistory(page.value, limit.value)
    if (res.code === 0 && res.data) {
      records.value = res.data.list || []
      total.value = res.data.total || 0
    } else {
      uni.showToast({ title: res.msg || '加载失败', icon: 'none' })
    }
  } catch (e) {
    console.error('加载记录失败:', e)
    uni.showToast({ title: '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

function prevPage() {
  if (page.value > 1) {
    page.value--
    loadHistory()
  }
}

function nextPage() {
  if (page.value < Math.ceil(total.value / limit.value)) {
    page.value++
    loadHistory()
  }
}

function goToTts() {
  uni.navigateTo({ url: '/pages/tts/tts' })
}

function selectRecord(record) {
  const voiceUrl = getRecordVoiceUrl(record)
  if (record.status !== 1 || !voiceUrl) {
    uni.showToast({ title: '该记录无可用音频', icon: 'none' })
    return
  }
  // 显示操作菜单
  uni.showActionSheet({
    itemList: ['播放音频', '保存到本地', '用于视频合成'],
    success: (res) => {
      if (res.tapIndex === 0) {
        playRecord(record)
      } else if (res.tapIndex === 1) {
        downloadRecord(record)
      } else if (res.tapIndex === 2) {
        useForVideo(record)
      }
    },
  })
}

function getRecordVoiceUrl(record) {
  return record.voice_url || record.voiceUrl || record.voiceURL || record.voice || ''
}

function stopAndDestroyAudio() {
  if (audioCtx) {
    try {
      audioCtx.stop()
      audioCtx.destroy()
    } catch (e) {
      console.error('停止播放失败:', e)
    }
    audioCtx = null
  }
  playing.value = false
  playingRecordId.value = null
  playingTempPath.value = ''
}

async function playRecord(record) {
  const voiceUrl = getRecordVoiceUrl(record)
  if (!voiceUrl) {
    uni.showToast({ title: '音频地址不存在', icon: 'none' })
    return
  }

  // 如果同一条记录已下载过，直接播本地临时文件
  if (playingRecordId.value === record.id && playingTempPath.value) {
    stopAndDestroyAudio()
    audioCtx = uni.createInnerAudioContext()
    audioCtx.src = playingTempPath.value
    audioCtx.onPlay(() => { playing.value = true })
    audioCtx.onEnded(() => { stopAndDestroyAudio() })
    audioCtx.onError(() => { stopAndDestroyAudio() })
    audioCtx.play()
    return
  }

  const url = ttsDownloadUrl(voiceUrl)

  stopAndDestroyAudio()
  playing.value = true
  playingRecordId.value = record.id

  uni.showLoading({ title: '下载音频...' })
  try {
    const dl = await downloadFileWithAuth(url, 60000)
    uni.hideLoading()

    playingTempPath.value = dl.tempFilePath

    audioCtx = uni.createInnerAudioContext()
    audioCtx.src = dl.tempFilePath
    audioCtx.onPlay(() => { playing.value = true })
    audioCtx.onEnded(() => { stopAndDestroyAudio() })
    audioCtx.onError((err) => {
      console.error('播放失败:', err)
      stopAndDestroyAudio()
      uni.showToast({ title: '播放失败', icon: 'none' })
    })
    audioCtx.play()
  } catch (e) {
    uni.hideLoading()
    stopAndDestroyAudio()
    uni.showToast({ title: e.message || '下载失败', icon: 'none' })
  }
}

function stopAudio() {
  stopAndDestroyAudio()
}

function downloadRecord(record) {
  const voiceUrl = getRecordVoiceUrl(record)
  if (!voiceUrl) {
    uni.showToast({ title: '音频地址不存在', icon: 'none' })
    return
  }

  const url = ttsDownloadUrl(voiceUrl)

  uni.showLoading({ title: '下载中...' })

  downloadFileWithAuth(url, 60000)
    .then((res) => {
      uni.saveFile({
        tempFilePath: res.tempFilePath,
        success: (saveRes) => {
          uni.hideLoading()
          uni.showToast({ title: '保存成功', icon: 'success' })
          console.log('文件保存路径:', saveRes.savedFilePath)
        },
        fail: () => {
          uni.hideLoading()
          uni.showToast({ title: '保存失败', icon: 'none' })
        },
      })
    })
    .catch(() => {
      uni.hideLoading()
      uni.showToast({ title: '下载失败', icon: 'none' })
    })
}

function useForVideo(record) {
  const voiceUrl = getRecordVoiceUrl(record)
  if (!voiceUrl) {
    uni.showToast({ title: '音频地址不存在', icon: 'none' })
    return
  }

  // 跳转到视频合成页面，并传递音频 URL
  uni.navigateTo({
    url: `/pages/synthesis/synthesis?audioUrl=${encodeURIComponent(voiceUrl)}`,
  })
}
</script>

<style scoped>
.history-page {
  min-height: 100vh;
  background: #f1f4fa;
  padding: 24rpx;
}

.action-bar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 24rpx;
}

.loading-view,
.empty-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120rpx 40rpx;
}

.loading-text {
  font-size: 28rpx;
  color: #64748b;
}

.empty-icon {
  font-size: 120rpx;
  margin-bottom: 24rpx;
}

.empty-text {
  font-size: 28rpx;
  color: #94a3b8;
}

.records-list {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.record-card {
  background: white;
  border-radius: 16rpx;
  padding: 24rpx;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.05);
}

.record-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16rpx;
}

.record-id {
  font-size: 28rpx;
  font-weight: 600;
  color: #1e293b;
}

.record-status {
  font-size: 24rpx;
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
}

.record-status.success {
  background: #dcfce7;
  color: #16a34a;
}

.record-status.error {
  background: #fee2e2;
  color: #dc2626;
}

.record-info {
  display: flex;
  margin-bottom: 8rpx;
}

.record-label {
  font-size: 26rpx;
  color: #64748b;
  min-width: 100rpx;
}

.record-value {
  font-size: 26rpx;
  color: #1e293b;
}

.record-error {
  margin-top: 12rpx;
  padding: 12rpx;
  background: #fef2f2;
  border-radius: 8rpx;
}

.error-text {
  font-size: 24rpx;
  color: #dc2626;
}

.record-actions {
  display: flex;
  gap: 12rpx;
  margin-top: 16rpx;
  padding-top: 16rpx;
  border-top: 1rpx solid #e2e8f0;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 24rpx;
  margin-top: 40rpx;
  padding: 24rpx 0;
}

.page-info {
  font-size: 28rpx;
  color: #64748b;
}

.playing-toast {
  position: fixed;
  bottom: 120rpx;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 16rpx 32rpx;
  border-radius: 48rpx;
  display: flex;
  align-items: center;
  gap: 16rpx;
  z-index: 9999;
}

.playing-text {
  font-size: 26rpx;
  color: white;
}
</style>
