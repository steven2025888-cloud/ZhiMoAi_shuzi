<template>
  <view class="mine-page">
    <!-- 用户卡片 -->
    <view class="user-card">
      <view class="user-avatar">
        <text class="avatar-text">🎭</text>
      </view>
      <view class="user-info">
        <text class="user-name">织梦AI · 手机版</text>
        <view class="license-row">
          <text class="license-label">卡密：</text>
          <text class="license-key">{{ maskedKey }}</text>
        </view>
        <text class="expire-text">到期：{{ expireTime || '永久' }}</text>
      </view>
    </view>

    <!-- Tab 切换：资产管理 -->
    <view class="tab-bar">
      <view class="tab-item" :class="{ active: activeTab === 'voice' }" @tap="activeTab = 'voice'">
        <text>🎵 音色 ({{ voiceList.length }})</text>
      </view>
      <view class="tab-item" :class="{ active: activeTab === 'avatar' }" @tap="activeTab = 'avatar'">
        <text>🎭 数字人 ({{ avatarList.length }})</text>
      </view>
    </view>

    <!-- 音色列表 -->
    <view v-if="activeTab === 'voice'" class="asset-section">
      <view class="asset-header">
        <text class="asset-title">我的音色</text>
        <z-button size="xs" type="primary" text="+ 上传音色" round @click="uploadVoice" />
      </view>

      <view v-if="assetsLoading" class="loading-row">
        <text class="loading-text">加载中...</text>
      </view>

      <view v-else-if="voiceList.length === 0" class="empty-row">
        <text class="empty-text">暂无音色，点击上方"上传音色"添加</text>
      </view>

      <view v-for="item in voiceList" :key="item.id" class="asset-item">
        <view class="asset-info">
          <text class="asset-name">🎵 {{ item.name }}</text>
          <text class="asset-meta">{{ formatSize(item.file_size) }} · 剩余{{ item.days_left }}天</text>
        </view>
        <z-button size="xs" type="danger" text="删除" @click="confirmDelete(item)" />
      </view>
    </view>

    <!-- 数字人列表 -->
    <view v-if="activeTab === 'avatar'" class="asset-section">
      <view class="asset-header">
        <text class="asset-title">我的数字人</text>
        <z-button size="xs" type="primary" text="+ 上传数字人" round @click="uploadAvatarFile" />
      </view>

      <view v-if="assetsLoading" class="loading-row">
        <text class="loading-text">加载中...</text>
      </view>

      <view v-else-if="avatarList.length === 0" class="empty-row">
        <text class="empty-text">暂无数字人，点击上方"上传数字人"添加视频</text>
      </view>

      <view v-for="item in avatarList" :key="item.id" class="asset-item">
        <view class="asset-info">
          <text class="asset-name">🎭 {{ item.name }}</text>
          <text class="asset-meta">{{ formatSize(item.file_size) }} · 剩余{{ item.days_left }}天</text>
        </view>
        <z-button size="xs" type="danger" text="删除" @click="confirmDelete(item)" />
      </view>
    </view>

    <!-- 上传进度 -->
    <view v-if="uploading" class="upload-overlay">
      <view class="upload-modal">
        <text class="upload-msg">{{ uploadMsg }}</text>
      </view>
    </view>

    <!-- 操作 -->
    <view class="card">
      <view class="action-item" @tap="clearCache">
        <text class="action-icon">🗑️</text>
        <text class="action-text">清除缓存</text>
        <text class="action-arrow">›</text>
      </view>
      <view class="divider"></view>
      <view class="action-item danger" @tap="handleLogout">
        <text class="action-icon">🚪</text>
        <text class="action-text">退出登录</text>
        <text class="action-arrow">›</text>
      </view>
    </view>

    <view class="footer">
      <text class="footer-text">织梦AI v1.0.0 · 手机版</text>
      <text class="footer-text">资产上传后保留30天，过期自动清理</text>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getLicenseKey, getExpireTime, logout, isLoggedIn } from '@/utils/storage.js'
import { listAssets, deleteAsset, uploadAsset } from '@/utils/api.js'
import { pickAudioFile } from '@/utils/file-picker.js'

const licenseKey = ref(getLicenseKey())
const expireTime = ref(getExpireTime())
const activeTab = ref('voice')
const assetsLoading = ref(false)
const voiceList = ref([])
const avatarList = ref([])
const uploading = ref(false)
const uploadMsg = ref('')

const maskedKey = computed(() => {
  const k = licenseKey.value
  if (!k || k.length < 10) return k
  return k.substring(0, 12) + '****' + k.substring(k.length - 4)
})

onMounted(() => {
  if (!isLoggedIn()) {
    uni.redirectTo({ url: '/pages/login/login' })
    return
  }

  // 检查是否从首页跳转过来指定tab
  const goTab = uni.getStorageSync('_go_tab')
  if (goTab) {
    activeTab.value = goTab
    uni.removeStorageSync('_go_tab')
  }

  loadAllAssets()
})

async function loadAllAssets() {
  assetsLoading.value = true
  try {
    const res = await listAssets('')
    if (res.code === 0 && Array.isArray(res.data)) {
      voiceList.value = res.data.filter(a => a.asset_type === 'voice')
      avatarList.value = res.data.filter(a => a.asset_type === 'avatar')
    }
  } catch (e) {
    console.error('loadAllAssets:', e)
  } finally {
    assetsLoading.value = false
  }
}

function formatSize(bytes) {
  if (!bytes) return '0B'
  if (bytes < 1024) return bytes + 'B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB'
  return (bytes / 1024 / 1024).toFixed(1) + 'MB'
}

async function uploadVoice() {
  try {
    const { path, name: fileName } = await pickAudioFile()
    const name = fileName ? fileName.replace(/\.\w+$/, '') : '新音色'
    await doUpload(path, 'voice', name)
  } catch (e) {
    if (e.message !== 'cancel') {
      uni.showToast({ title: e.message || '选择文件失败', icon: 'none' })
    }
  }
}

function uploadAvatarFile() {
  // #ifdef H5 || APP-PLUS
  uni.chooseVideo({
    count: 1,
    sourceType: ['album'],
    success: async (res) => {
      const name = '新数字人_' + Date.now()
      await doUpload(res.tempFilePath, 'avatar', name)
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
      await doUpload(file.path, 'avatar', name)
    },
  })
  // #endif
}

async function doUpload(filePath, assetType, name) {
  uploading.value = true
  uploadMsg.value = `正在上传${assetType === 'voice' ? '音色' : '数字人'}...`
  try {
    const upRes = await uploadAsset(filePath, assetType, name)
    if (upRes.code === 0) {
      uni.showToast({ title: '上传成功', icon: 'success' })
      await loadAllAssets()
    } else {
      uni.showToast({ title: upRes.msg || '上传失败', icon: 'none' })
    }
  } catch (e) {
    uni.showModal({ title: '上传失败', content: e.message || '网络错误', showCancel: false })
  } finally {
    uploading.value = false
    uploadMsg.value = ''
  }
}

function confirmDelete(item) {
  const label = item.asset_type === 'voice' ? '音色' : '数字人'
  uni.showModal({
    title: `删除${label}`,
    content: `确定删除「${item.name}」？删除后不可恢复`,
    confirmColor: '#ef4444',
    success: async (res) => {
        if (res.confirm) {
          try {
            const delRes = await deleteAsset(item.id)
            if (delRes.code === 0 && delRes.data?.queued) {
              // GPU 离线，任务已排队
              uni.showModal({
                title: '已排队',
                content: 'GPU服务器未上线，删除任务已排队，服务器启动后自动执行（约2分钟）',
                showCancel: false,
              })
            } else if (delRes.code === 0) {
              uni.showToast({ title: '已删除', icon: 'success' })
            } else {
              uni.showToast({ title: delRes.msg || '删除失败', icon: 'none' })
            }
            await loadAllAssets()
          } catch (e) {
            uni.showToast({ title: '删除失败', icon: 'none' })
          }
        }
    },
  })
}

function clearCache() {
  uni.showModal({
    title: '清除缓存',
    content: '将清除本地临时文件，不影响登录和已上传资产',
    success(res) {
      if (res.confirm) {
        uni.removeStorageSync('tts_result_url')
        uni.removeStorageSync('tts_result_text')
        uni.removeStorageSync('_edit_mode')
        uni.showToast({ title: '已清除', icon: 'success' })
      }
    },
  })
}

function handleLogout() {
  uni.showModal({
    title: '退出登录',
    content: '退出后需重新输入卡密登录',
    confirmColor: '#ef4444',
    success(res) {
      if (res.confirm) {
        logout()
        uni.redirectTo({ url: '/pages/login/login' })
      }
    },
  })
}
</script>

<style lang="scss" scoped>
.mine-page {
  min-height: 100vh;
  background: #f1f4fa;
  padding-bottom: 140rpx;
}

.user-card {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  padding: 50rpx 40rpx 40rpx;
  display: flex;
  align-items: center;
  gap: 24rpx;
}

.user-avatar {
  width: 100rpx; height: 100rpx; border-radius: 50%;
  background: rgba(255,255,255,0.2);
  display: flex; align-items: center; justify-content: center;
}

.avatar-text { font-size: 50rpx; }
.user-info { flex: 1; }
.user-name { font-size: 34rpx; font-weight: 700; color: #fff; display: block; }
.license-row { display: flex; align-items: center; margin-top: 8rpx; }
.license-label { font-size: 22rpx; color: rgba(255,255,255,0.7); }
.license-key { font-size: 22rpx; color: rgba(255,255,255,0.9); font-family: monospace; }
.expire-text { font-size: 20rpx; color: rgba(255,255,255,0.6); margin-top: 4rpx; display: block; }

.tab-bar {
  display: flex;
  margin: 24rpx 30rpx 0;
  background: #fff;
  border-radius: 16rpx;
  overflow: hidden;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
}

.tab-item {
  flex: 1;
  padding: 24rpx 0;
  text-align: center;
  font-size: 26rpx;
  color: #64748b;
  border-bottom: 4rpx solid transparent;
  &.active { color: #6366f1; border-bottom-color: #6366f1; font-weight: 600; }
}

.asset-section {
  margin: 16rpx 30rpx 0;
}

.asset-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16rpx;
}

.asset-title { font-size: 28rpx; font-weight: 600; color: #334155; }

.asset-item {
  display: flex;
  align-items: center;
  background: #fff;
  border-radius: 16rpx;
  padding: 20rpx 24rpx;
  margin-bottom: 12rpx;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.03);
}

.asset-info { flex: 1; }
.asset-name { font-size: 26rpx; color: #1e293b; font-weight: 500; display: block; }
.asset-meta { font-size: 20rpx; color: #94a3b8; margin-top: 4rpx; display: block; }

.loading-row, .empty-row { padding: 40rpx 0; text-align: center; }
.loading-text, .empty-text { font-size: 24rpx; color: #94a3b8; }

.upload-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.4); z-index: 999;
  display: flex; align-items: center; justify-content: center;
}

.upload-modal {
  background: #fff; border-radius: 20rpx; padding: 40rpx 60rpx;
}

.upload-msg { font-size: 28rpx; color: #334155; }

.card {
  background: #fff; border-radius: 20rpx;
  margin: 24rpx 30rpx 0; padding: 10rpx 30rpx;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.04);
}

.divider { height: 1rpx; background: #f1f5f9; }

.action-item {
  display: flex; align-items: center; padding: 28rpx 0; gap: 16rpx;
  &.danger .action-text { color: #ef4444; }
}

.action-icon { font-size: 32rpx; }
.action-text { flex: 1; font-size: 28rpx; color: #334155; }
.action-arrow { font-size: 32rpx; color: #cbd5e1; }

.footer { padding: 40rpx 0; text-align: center; }
.footer-text { font-size: 22rpx; color: #cbd5e1; display: block; line-height: 1.8; }
</style>
