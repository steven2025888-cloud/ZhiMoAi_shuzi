<template>
  <view class="home-page">
    <view class="home-header">
      <text class="header-title">🎭 织梦AI</text>
      <text class="header-sub">手机端 · 在线合成</text>
    </view>

    <!-- 功能网格 -->
    <view class="section-title">核心功能</view>
    <view class="func-grid">
      <view class="func-card" @tap="goTTS">
        <view class="func-icon" style="background: linear-gradient(135deg, #06b6d4, #0891b2);">
          <text class="icon-text">🎙️</text>
        </view>
        <text class="func-name">语音合成</text>
        <text class="func-desc">在线TTS配音</text>
      </view>

      <view class="func-card" @tap="goSynthesis">
        <view class="func-icon" style="background: linear-gradient(135deg, #8b5cf6, #7c3aed);">
          <text class="icon-text">🎬</text>
        </view>
        <text class="func-name">视频合成</text>
        <text class="func-desc">数字人驱动</text>
      </view>

      <view class="func-card" @tap="goUploadVoice">
        <view class="func-icon" style="background: linear-gradient(135deg, #f59e0b, #d97706);">
          <text class="icon-text">🎵</text>
        </view>
        <text class="func-name">上传音色</text>
        <text class="func-desc">{{ voiceCount }}个音色</text>
      </view>

      <view class="func-card" @tap="goUploadAvatar">
        <view class="func-icon" style="background: linear-gradient(135deg, #10b981, #059669);">
          <text class="icon-text">🎭</text>
        </view>
        <text class="func-name">上传数字人</text>
        <text class="func-desc">{{ avatarCount }}个数字人</text>
      </view>
    </view>

    <!-- 资产概览 -->
    <view class="section-title">我的资产</view>
    <view class="asset-card">
      <view class="asset-row">
        <text class="asset-label">🎵 音色</text>
        <text class="asset-value">{{ voiceCount }} 个</text>
      </view>
      <view class="asset-divider"></view>
      <view class="asset-row">
        <text class="asset-label">🎭 数字人</text>
        <text class="asset-value">{{ avatarCount }} 个</text>
      </view>
      <view class="asset-divider"></view>
      <view class="asset-row">
        <text class="asset-label">📋 有效期</text>
        <text class="asset-value">上传后保留30天</text>
      </view>
    </view>

    <!-- 快速入口 -->
    <view class="section-title">视频后期</view>
    <view class="edit-grid">
      <view class="edit-card" @tap="goEditPage('subtitle')">
        <text class="edit-icon">📝</text>
        <text class="edit-name">加字幕</text>
      </view>
      <view class="edit-card" @tap="goEditPage('pip')">
        <text class="edit-icon">🖼</text>
        <text class="edit-name">画中画</text>
      </view>
      <view class="edit-card" @tap="goEditPage('bgm')">
        <text class="edit-icon">🎵</text>
        <text class="edit-name">加BGM</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { isLoggedIn } from '@/utils/storage.js'
import { listAssets } from '@/utils/api.js'

const voiceCount = ref(0)
const avatarCount = ref(0)

onMounted(async () => {
  if (!isLoggedIn()) {
    uni.redirectTo({ url: '/pages/login/login' })
    return
  }
  loadAssetCounts()
})

async function loadAssetCounts() {
  try {
    const res = await listAssets('')
    if (res.code === 0 && Array.isArray(res.data)) {
      voiceCount.value = res.data.filter(a => a.asset_type === 'voice').length
      avatarCount.value = res.data.filter(a => a.asset_type === 'avatar').length
    }
  } catch (e) {
    console.error('loadAssetCounts:', e)
  }
}

function goTTS() { uni.switchTab({ url: '/pages/tts/tts' }) }
function goSynthesis() { uni.switchTab({ url: '/pages/synthesis/synthesis' }) }
function goMine() { uni.switchTab({ url: '/pages/mine/mine' }) }

function goUploadVoice() {
  uni.switchTab({ url: '/pages/mine/mine' })
  // mine页会显示资产管理
  uni.setStorageSync('_go_tab', 'voice')
}

function goUploadAvatar() {
  uni.switchTab({ url: '/pages/mine/mine' })
  uni.setStorageSync('_go_tab', 'avatar')
}

function goEditPage(editType) {
  // 跳到合成页并标记编辑模式
  uni.setStorageSync('_edit_mode', editType)
  uni.switchTab({ url: '/pages/synthesis/synthesis' })
}
</script>

<style lang="scss" scoped>
.home-page {
  min-height: 100vh;
  background: #f1f4fa;
  padding-bottom: 120rpx;
}

.home-header {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  padding: 40rpx 40rpx 50rpx;
}

.header-title { font-size: 40rpx; font-weight: 700; color: #fff; display: block; }
.header-sub { font-size: 24rpx; color: rgba(255,255,255,0.7); margin-top: 8rpx; display: block; }

.section-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #334155;
  padding: 30rpx 40rpx 16rpx;
}

.func-grid {
  display: flex;
  flex-wrap: wrap;
  padding: 0 30rpx;
  gap: 20rpx;
}

.func-card {
  width: calc(50% - 10rpx);
  background: #fff;
  border-radius: 20rpx;
  padding: 30rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.04);
}

.func-icon {
  width: 90rpx; height: 90rpx; border-radius: 24rpx;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 16rpx;
}

.icon-text { font-size: 44rpx; }
.func-name { font-size: 28rpx; font-weight: 600; color: #1e293b; }
.func-desc { font-size: 22rpx; color: #94a3b8; margin-top: 4rpx; }

.asset-card {
  margin: 0 30rpx;
  background: #fff;
  border-radius: 20rpx;
  padding: 10rpx 30rpx;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.04);
}

.asset-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24rpx 0;
}

.asset-label { font-size: 26rpx; color: #64748b; }
.asset-value { font-size: 26rpx; color: #1e293b; font-weight: 500; }
.asset-divider { height: 1rpx; background: #f1f5f9; }

.edit-grid {
  display: flex;
  padding: 0 30rpx;
  gap: 20rpx;
}

.edit-card {
  flex: 1;
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
}

.edit-icon { font-size: 40rpx; margin-bottom: 8rpx; }
.edit-name { font-size: 24rpx; color: #334155; font-weight: 500; }
</style>
