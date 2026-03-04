<template>
  <view class="login-page">
    <view class="login-header">
      <view class="login-logo">
        <text class="logo-icon">🎭</text>
        <text class="logo-title">织梦AI</text>
        <text class="logo-subtitle">数字人视频合成 · 手机版</text>
      </view>
    </view>

    <view class="login-card">
      <view class="card-title">卡密登录</view>

      <view class="field-group">
        <text class="field-label">请输入卡密</text>
        <z-input
          v-model="licenseKey"
          placeholder="ZM-XXXXXXXX-XXXXXXXXXX"
          :clearable="true"
        >
          <template #prefix>
            <text class="field-icon">🔑</text>
          </template>
        </z-input>
      </view>

      <view style="margin-top: 40rpx;">
        <z-button
          type="primary"
          size="lg"
          :text="loading ? '登录中...' : '登 录'"
          :loading="loading"
          :disabled="loading || !licenseKey.trim()"
          block
          round
          @click="handleLogin"
        />
      </view>

      <view class="login-tips">
        <text class="tip-text">· 手机端需要在线版卡密才能使用</text>
        <text class="tip-text">· 每个卡密支持 1台电脑 + 1部手机同时在线</text>
        <text class="tip-text">· 新手机登录将自动踢掉旧手机会话</text>
        <text class="tip-text">· 音色和数字人从手机直接上传管理</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { login as apiLogin } from '@/utils/api.js'
import { saveLicense, isLoggedIn } from '@/utils/storage.js'
import { connect as wsConnect } from '@/utils/websocket.js'

const licenseKey = ref('')
const loading = ref(false)

onMounted(() => {
  if (isLoggedIn()) {
    uni.switchTab({ url: '/pages/index/index' })
  }
})

async function handleLogin() {
  const key = licenseKey.value.trim()
  if (!key) {
    uni.showToast({ title: '请输入卡密', icon: 'none' })
    return
  }

  loading.value = true
  try {
    const res = await apiLogin(key)
    if (res.code === 0) {
      saveLicense({
        license_key: key,
        expire_time: res.expire_time || '',
        online_enabled: res.online_enabled || 0,
        synthesis_server_url: res.synthesis_server_url || 'http://117.50.91.129:8383',
        synthesis_api_secret: res.synthesis_api_secret || '',
        session_token: res.session_token || '',
      })
      uni.showToast({ title: '登录成功', icon: 'success' })
      // 登录成功后建立 WS 连接（onLaunch 时未登录所以跳过了）
      wsConnect()
      setTimeout(() => {
        uni.switchTab({ url: '/pages/index/index' })
      }, 800)
    } else {
      uni.showModal({
        title: '登录失败',
        content: res.msg || '未知错误',
        showCancel: false,
      })
    }
  } catch (e) {
    uni.showModal({
      title: '连接失败',
      content: e.message || '无法连接服务器',
      showCancel: false,
    })
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  background: #f1f4fa;
}

.login-header {
  height: 480rpx;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a78bfa 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0 0 60rpx 60rpx;
}

.login-logo {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 60rpx;
}

.logo-icon { font-size: 100rpx; margin-bottom: 20rpx; }
.logo-title { font-size: 48rpx; font-weight: 700; color: #fff; letter-spacing: 4rpx; }
.logo-subtitle { font-size: 24rpx; color: rgba(255,255,255,0.75); margin-top: 12rpx; }

.login-card {
  margin: -80rpx 40rpx 0;
  padding: 50rpx 40rpx;
  background: #fff;
  border-radius: 24rpx;
  box-shadow: 0 8rpx 40rpx rgba(99,102,241,0.12);
}

.card-title { font-size: 36rpx; font-weight: 700; color: #1e293b; margin-bottom: 40rpx; text-align: center; }
.field-group { margin-bottom: 30rpx; }
.field-label { font-size: 26rpx; color: #64748b; margin-bottom: 12rpx; display: block; }
.field-icon { font-size: 32rpx; margin-right: 12rpx; }

.login-tips {
  margin-top: 40rpx;
  padding-top: 30rpx;
  border-top: 1rpx solid #f1f5f9;
}

.tip-text { display: block; font-size: 22rpx; color: #94a3b8; line-height: 2; }
</style>
