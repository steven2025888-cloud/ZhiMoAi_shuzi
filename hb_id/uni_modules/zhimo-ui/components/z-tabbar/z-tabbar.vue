<template>
	<view class="z-tabbar" :class="[fixed ? 'z-tabbar--fixed' : '', `z-tabbar--${theme}`]"
		:style="{ background: bgColor, zIndex: zIndex }">
		<!-- 凹陷背景层（高科技凹陷效果） -->
		<view v-if="concave && hasCenterButton" class="z-tabbar__concave" :style="{ background: bgColor }">
			<view class="z-tabbar__concave-curve" :style="{ background: concaveBg }"></view>
		</view>

		<!-- 主内容区 -->
		<view class="z-tabbar__content" :class="[border ? 'z-tabbar--border' : '']"
			:style="{ borderColor: borderColor }">
			<view class="z-tabbar__item" v-for="(item, index) in tabList" :key="index" @tap="handleClick(index, item)"
				:class="[item.center ? 'z-tabbar__item--center' : '']">

				<!-- 中间凸起按钮 -->
				<view v-if="item.center" class="z-tabbar__center-btn"
					:class="[`z-tabbar__center-btn--${centerStyle}`, activeIndex === index ? 'z-tabbar__center-btn--active' : '']"
					:style="getCenterBtnStyle(item)">
					<image v-if="item.icon" class="z-tabbar__center-icon" :src="item.icon"
						:style="{ width: (item.iconSize || 48) + 'rpx', height: (item.iconSize || 48) + 'rpx' }" />
					<text v-else-if="item.text" class="z-tabbar__center-text" :style="{ color: item.color || '#fff' }">{{
						item.text }}</text>
				</view>

				<!-- 普通按钮 -->
				<template v-else>
					<!-- 选中指示器 -->
					<view v-if="indicator && activeIndex === index" class="z-tabbar__indicator"
						:class="[`z-tabbar__indicator--${indicatorStyle}`]" :style="{ background: activeColor }">
					</view>

					<!-- 图标区域 -->
					<view class="z-tabbar__icon-wrap" v-if="item.icon || item.activeIcon">
						<image class="z-tabbar__icon"
							:src="activeIndex === index ? (item.activeIcon || item.icon) : item.icon"
							:style="{ width: iconSize + 'rpx', height: iconSize + 'rpx' }" />
						<!-- 角标 -->
						<view v-if="item.badge" class="z-tabbar__badge"
							:class="[item.dot ? 'z-tabbar__badge--dot' : '']" :style="{ background: badgeBg }">
							<text v-if="!item.dot" class="z-tabbar__badge-text" :style="{ color: badgeColor }">{{
								formatBadge(item.badge) }}</text>
						</view>
					</view>

					<!-- 文字 -->
					<text v-if="item.text" class="z-tabbar__text"
						:style="{ color: activeIndex === index ? activeColor : color, fontSize: fontSize + 'rpx', fontWeight: activeIndex === index ? fontWeightActive : fontWeight }">
						{{ item.text }}
					</text>
				</template>
			</view>
		</view>

		<!-- 底部安全区 -->
		<view v-if="safeArea && fixed" class="z-tabbar__safe"></view>
	</view>
</template>

<script>
	/**
	 * z-tabbar 底部导航栏
	 * @description 高科技风格底部导航栏组件，支持凸起/凹陷效果、多种主题、角标等
	 * @property {Array} list - 导航项列表
	 * @property {Number} active - 当前激活项索引
	 * @property {String} theme - 主题风格：default/dark/glass/gradient/neon
	 * @property {Boolean} fixed - 是否固定底部
	 * @property {Boolean} border - 是否显示顶部边框
	 * @property {Boolean} safeArea - 是否适配底部安全区
	 * @property {Boolean} concave - 是否显示凹陷效果（配合中间凸起按钮）
	 * @property {String} centerStyle - 中间按钮风格：circle/square/diamond/hexagon
	 * @property {Boolean} indicator - 是否显示选中指示器
	 * @property {String} indicatorStyle - 指示器风格：line/dot/pill/glow
	 * @event {Function} change - 切换时触发
	 * @event {Function} click - 点击时触发
	 */
	export default {
		name: 'z-tabbar',
		emits: ['update:active', 'change', 'click', 'init'],
		props: {
			// 导航项列表
			list: {
				type: Array,
				default: () => []
			},
			// 当前激活项
			active: {
				type: [Number, String],
				default: 0
			},
			// 主题：default/dark/glass/gradient/neon
			theme: {
				type: String,
				default: 'default'
			},
			// 是否固定底部
			fixed: {
				type: Boolean,
				default: true
			},
			// 是否显示边框
			border: {
				type: Boolean,
				default: true
			},
			// 边框颜色
			borderColor: {
				type: String,
				default: 'rgba(0, 0, 0, 0.05)'
			},
			// 背景色
			bgColor: {
				type: String,
				default: ''
			},
			// 文字颜色
			color: {
				type: String,
				default: '#999'
			},
			// 激活颜色
			activeColor: {
				type: String,
				default: '#6366f1'
			},
			// 字体大小
			fontSize: {
				type: [Number, String],
				default: 22
			},
			// 字重
			fontWeight: {
				type: [Number, String],
				default: 400
			},
			// 激活字重
			fontWeightActive: {
				type: [Number, String],
				default: 500
			},
			// 图标大小
			iconSize: {
				type: [Number, String],
				default: 48
			},
			// 角标背景色
			badgeBg: {
				type: String,
				default: '#ef4444'
			},
			// 角标文字颜色
			badgeColor: {
				type: String,
				default: '#fff'
			},
			// z-index
			zIndex: {
				type: [Number, String],
				default: 999
			},
			// 是否适配安全区
			safeArea: {
				type: Boolean,
				default: true
			},
			// 凹陷效果
			concave: {
				type: Boolean,
				default: false
			},
			// 凹陷背景色
			concaveBg: {
				type: String,
				default: '#f5f5f5'
			},
			// 中间按钮风格：circle/square/diamond/hexagon
			centerStyle: {
				type: String,
				default: 'circle'
			},
			// 选中指示器
			indicator: {
				type: Boolean,
				default: false
			},
			// 指示器风格：line/dot/pill/glow
			indicatorStyle: {
				type: String,
				default: 'line'
			}
		},
		data() {
			return {
				activeIndex: 0,
				safeAreaHeight: 0
			}
		},
		computed: {
			tabList() {
				if (!this.list || this.list.length === 0) return []
				return this.list.map(item => {
					if (typeof item === 'string') {
						return { text: item }
					}
					return item
				})
			},
			hasCenterButton() {
				return this.tabList.some(item => item.center)
			}
		},
		watch: {
			active: {
				immediate: true,
				handler(val) {
					this.activeIndex = Number(val)
				}
			}
		},
		created() {
			this.initSafeArea()
		},
		methods: {
			// 初始化安全区
			initSafeArea() {
				try {
					const res = uni.getSystemInfoSync()
					if (res.safeAreaInsets && res.safeAreaInsets.bottom > 0) {
						this.safeAreaHeight = res.safeAreaInsets.bottom
					}
				} catch (e) {
					console.warn('获取系统信息失败', e)
				}
				this.$emit('init', {
					height: uni.upx2px(100) + this.safeAreaHeight
				})
			},
			// 处理点击
			handleClick(index, item) {
				// 中间按钮特殊处理
				if (item.center) {
					this.$emit('click', { index, ...item, isCenter: true })
					return
				}

				const oldIndex = this.activeIndex
				this.activeIndex = index
				this.$emit('update:active', index)
				this.$emit('click', { index, ...item })

				if (oldIndex !== index) {
					this.$emit('change', { index, ...item })
				}
			},
			// 获取中间按钮样式
			getCenterBtnStyle(item) {
				const size = item.size || 112
				const bottom = item.bottom || 20
				const bg = item.bg || 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)'
				return {
					width: size + 'rpx',
					height: size + 'rpx',
					bottom: bottom + 'rpx',
					background: bg
				}
			},
			// 格式化角标
			formatBadge(badge) {
				if (typeof badge === 'number' && badge > 99) {
					return '99+'
				}
				return badge
			}
		}
	}
</script>

<style scoped>
	.z-tabbar {
		position: relative;
		width: 100%;
	}

	.z-tabbar--fixed {
		position: fixed;
		left: 0;
		right: 0;
		bottom: 0;
	}

	/* 主题样式 */
	.z-tabbar--default {
		background: #ffffff;
	}

	.z-tabbar--dark {
		background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
	}

	.z-tabbar--dark .z-tabbar__text {
		color: rgba(255, 255, 255, 0.6);
	}

	.z-tabbar--glass {
		background: rgba(255, 255, 255, 0.85);
		backdrop-filter: blur(20px);
		-webkit-backdrop-filter: blur(20px);
	}

	.z-tabbar--gradient {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
	}

	.z-tabbar--gradient .z-tabbar__text {
		color: rgba(255, 255, 255, 0.7);
	}

	.z-tabbar--neon {
		background: #0f0f23;
		box-shadow: 0 -4rpx 30rpx rgba(99, 102, 241, 0.3);
	}

	.z-tabbar--neon .z-tabbar__text {
		color: rgba(255, 255, 255, 0.5);
		text-shadow: 0 0 10rpx currentColor;
	}

	/* 凹陷效果 */
	.z-tabbar__concave {
		position: absolute;
		top: -40rpx;
		left: 50%;
		transform: translateX(-50%);
		width: 160rpx;
		height: 80rpx;
		z-index: 1;
	}

	.z-tabbar__concave-curve {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		border-radius: 0 0 80rpx 80rpx;
	}

	.z-tabbar__concave::before,
	.z-tabbar__concave::after {
		content: '';
		position: absolute;
		top: 0;
		width: 40rpx;
		height: 40rpx;
		background: transparent;
	}

	.z-tabbar__concave::before {
		left: -40rpx;
		border-radius: 0 40rpx 0 0;
		box-shadow: 20rpx 0 0 0 v-bind(concaveBg);
	}

	.z-tabbar__concave::after {
		right: -40rpx;
		border-radius: 40rpx 0 0 0;
		box-shadow: -20rpx 0 0 0 v-bind(concaveBg);
	}

	/* 内容区 */
	.z-tabbar__content {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: space-around;
		height: 100rpx;
		z-index: 2;
	}

	.z-tabbar--border {
		border-top: 1rpx solid rgba(0, 0, 0, 0.05);
	}

	/* 导航项 */
	.z-tabbar__item {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100rpx;
		position: relative;
		cursor: pointer;
	}

	.z-tabbar__item--center {
		position: relative;
	}

	/* 图标区域 */
	.z-tabbar__icon-wrap {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 56rpx;
		height: 56rpx;
	}

	.z-tabbar__icon {
		width: 48rpx;
		height: 48rpx;
		display: block;
	}

	/* 文字 */
	.z-tabbar__text {
		font-size: 22rpx;
		line-height: 1.2;
		margin-top: 4rpx;
		transition: all 0.2s ease;
	}

	/* 角标 */
	.z-tabbar__badge {
		position: absolute;
		top: -8rpx;
		right: -16rpx;
		min-width: 32rpx;
		height: 32rpx;
		padding: 0 8rpx;
		border-radius: 16rpx;
		display: flex;
		align-items: center;
		justify-content: center;
		box-sizing: border-box;
	}

	.z-tabbar__badge--dot {
		min-width: 16rpx;
		width: 16rpx;
		height: 16rpx;
		padding: 0;
		border-radius: 50%;
		top: -4rpx;
		right: -4rpx;
	}

	.z-tabbar__badge-text {
		font-size: 20rpx;
		line-height: 1;
	}

	/* 中间按钮 */
	.z-tabbar__center-btn {
		position: absolute;
		display: flex;
		align-items: center;
		justify-content: center;
		box-shadow: 0 8rpx 32rpx rgba(99, 102, 241, 0.4);
		transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
		z-index: 10;
	}

	.z-tabbar__center-btn:active {
		transform: scale(0.95);
	}

	.z-tabbar__center-btn--active {
		box-shadow: 0 12rpx 40rpx rgba(99, 102, 241, 0.6);
	}

	/* 圆形 */
	.z-tabbar__center-btn--circle {
		border-radius: 50%;
	}

	/* 方形圆角 */
	.z-tabbar__center-btn--square {
		border-radius: 24rpx;
	}

	/* 菱形 */
	.z-tabbar__center-btn--diamond {
		border-radius: 24rpx;
		transform: rotate(45deg);
	}

	.z-tabbar__center-btn--diamond .z-tabbar__center-icon,
	.z-tabbar__center-btn--diamond .z-tabbar__center-text {
		transform: rotate(-45deg);
	}

	/* 六边形（近似） */
	.z-tabbar__center-btn--hexagon {
		border-radius: 16rpx;
		clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
	}

	.z-tabbar__center-icon {
		width: 48rpx;
		height: 48rpx;
	}

	.z-tabbar__center-text {
		font-size: 24rpx;
		font-weight: 600;
	}

	/* 选中指示器 */
	.z-tabbar__indicator {
		position: absolute;
		transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	}

	/* 线条 */
	.z-tabbar__indicator--line {
		top: 0;
		width: 40rpx;
		height: 6rpx;
		border-radius: 0 0 6rpx 6rpx;
	}

	/* 圆点 */
	.z-tabbar__indicator--dot {
		bottom: 8rpx;
		width: 8rpx;
		height: 8rpx;
		border-radius: 50%;
	}

	/* 药丸 */
	.z-tabbar__indicator--pill {
		top: 50%;
		transform: translateY(-50%);
		width: 100rpx;
		height: 64rpx;
		border-radius: 32rpx;
		opacity: 0.15;
		z-index: -1;
	}

	/* 发光 */
	.z-tabbar__indicator--glow {
		bottom: 0;
		width: 60rpx;
		height: 4rpx;
		border-radius: 4rpx;
		box-shadow: 0 0 20rpx currentColor, 0 0 40rpx currentColor;
	}

	/* 安全区 */
	.z-tabbar__safe {
		width: 100%;
		padding-bottom: constant(safe-area-inset-bottom);
		padding-bottom: env(safe-area-inset-bottom);
	}
</style>
