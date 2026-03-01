<template>
	<view v-if="show" class="z-captcha">
		<view class="z-captcha__mask" @tap="onMaskTap" />
		<view class="z-captcha__dialog" :class="{ 'z-captcha__dialog--shake': shaking }">
			<!-- 头部 -->
			<view class="z-captcha__header">
				<text class="z-captcha__title">{{ titleText }}</text>
				<view class="z-captcha__header-actions">
					<view class="z-captcha__header-btn" @tap="doReset">
						<text class="z-captcha__header-btn-text">↻</text>
					</view>
					<view class="z-captcha__header-btn" @tap="doClose">
						<text class="z-captcha__header-btn-text">×</text>
					</view>
				</view>
			</view>

			<!-- 提示 -->
			<view class="z-captcha__tip">
				<text class="z-captcha__tip-text">{{ tipText }}</text>
			</view>

			<!-- ========== 拼图模式 ========== -->
			<view v-if="mode === 'puzzle'" class="z-captcha__visual z-captcha__puzzle-area">
				<view class="z-captcha__puzzle-bg">
					<view v-for="(d, i) in puzzleDeco" :key="i" class="z-captcha__puzzle-deco"
						:style="{ left: d.x + '%', top: d.y + '%', fontSize: d.size + 'rpx' }">
						<text>{{ d.emoji }}</text>
					</view>
				</view>
				<view class="z-captcha__puzzle-hole" :style="{ left: puzzleTarget + 'px' }" />
				<view class="z-captcha__puzzle-piece" :style="{ left: sliderX + 'px' }">
					<view class="z-captcha__puzzle-piece-inner" />
				</view>
			</view>

			<!-- ========== 旋转模式 ========== -->
			<view v-if="mode === 'rotate'" class="z-captcha__visual z-captcha__rotate-area">
				<view class="z-captcha__rotate-outer">
					<view class="z-captcha__rotate-ring"
						:style="{ transform: 'rotate(' + rotateCurrent + 'deg)' }">
						<view class="z-captcha__rotate-dot" />
						<text class="z-captcha__rotate-emoji">{{ rotateEmoji }}</text>
					</view>
				</view>
			</view>

			<!-- ========== 文字点选模式 ========== -->
			<view v-if="mode === 'order'" class="z-captcha__visual z-captcha__order-area">
				<view v-for="(ch, i) in orderItems" :key="i" class="z-captcha__order-item"
					:class="{
						'z-captcha__order-item--done': orderDone.includes(i),
						'z-captcha__order-item--wrong': orderWrong === i
					}" :style="{ left: ch.x + '%', top: ch.y + '%' }" @tap.stop="onOrderTap(i)">
					<text class="z-captcha__order-item-text">{{ ch.text }}</text>
					<view v-if="orderDone.includes(i)" class="z-captcha__order-seq">
						<text class="z-captcha__order-seq-text">{{ orderDone.indexOf(i) + 1 }}</text>
					</view>
				</view>
			</view>

			<!-- ========== 算术模式 ========== -->
			<view v-if="mode === 'math'" class="z-captcha__visual z-captcha__math-area">
				<text class="z-captcha__math-expr">{{ mathA }} {{ mathOp }} {{ mathB }} = ?</text>
				<text class="z-captcha__math-val" :class="{ 'z-captcha__math-val--match': mathCurrVal === mathAnswer }">
					{{ mathCurrVal }}
				</text>
			</view>

			<!-- ========== 图标点选模式 ========== -->
			<view v-if="mode === 'icon'" class="z-captcha__visual z-captcha__icon-area">
				<view class="z-captcha__icon-grid">
					<view v-for="(cell, i) in iconGrid" :key="i" class="z-captcha__icon-cell"
						:class="{
							'z-captcha__icon-cell--done': iconDone.includes(i),
							'z-captcha__icon-cell--wrong': iconWrong === i
						}" @tap.stop="onIconTap(i)">
						<text class="z-captcha__icon-cell-text">{{ cell.emoji }}</text>
					</view>
				</view>
			</view>

			<!-- ========== 滑块轨道（slide/puzzle/rotate/math 共用）========== -->
			<view v-if="needSlider" class="z-captcha__slider-box">
				<view class="z-captcha__track" id="captchaTrack">
					<view class="z-captcha__track-fill"
						:style="{ width: (sliderX + btnHalf) + 'px', background: fillColor }" />
					<text v-if="sliderX < 3 && status === 'pending'" class="z-captcha__track-hint">
						{{ sliderHint }}
					</text>
					<view class="z-captcha__handle" :class="{ 'z-captcha__handle--spring': springing }"
						:style="{ left: sliderX + 'px', background: handleBg }"
						@touchstart="onDragStart" @touchmove.stop.prevent="onDragMove" @touchend="onDragEnd">
						<text class="z-captcha__handle-icon">{{ handleIcon }}</text>
					</view>
				</view>
				<view v-if="mode === 'math'" class="z-captcha__math-labels">
					<text class="z-captcha__math-label">0</text>
					<text class="z-captcha__math-label">{{ mathMax }}</text>
				</view>
			</view>

			<!-- ========== 结果蒙层 ========== -->
			<view v-if="status !== 'pending'" class="z-captcha__result" :class="'z-captcha__result--' + status">
				<text class="z-captcha__result-icon">{{ status === 'success' ? '✓' : '✗' }}</text>
				<text class="z-captcha__result-text">{{ status === 'success' ? '验证成功' : '验证失败' }}</text>
				<text v-if="status === 'success'" class="z-captcha__result-time">用时 {{ elapsed }}s</text>
			</view>
		</view>
	</view>
</template>

<script setup>
/**
 * z-captcha 滑动验证码
 * @description 多模式验证码组件：滑动到底、拼图滑块、旋转验证、文字点选、算术验证、图标点选
 * @property {String}  mode       验证模式 slide|puzzle|rotate|order|math|icon（默认 slide）
 * @property {Boolean} show       是否显示（v-model:show）
 * @property {String}  title      自定义标题
 * @property {Boolean} maskClose  点击遮罩关闭（默认 true）
 * @property {Number}  tolerance  拼图/旋转容差 px（默认 8）
 * @event {Function} success 验证成功
 * @event {Function} fail    验证失败
 * @event {Function} close   关闭弹窗
 */
import { ref, computed, watch, nextTick, getCurrentInstance } from 'vue'

const instance = getCurrentInstance()

const props = defineProps({
	mode: { type: String, default: 'slide' },
	show: { type: Boolean, default: false },
	title: { type: String, default: '' },
	maskClose: { type: Boolean, default: true },
	tolerance: { type: Number, default: 8 }
})

const emit = defineEmits(['update:show', 'success', 'fail', 'close'])

// ======================== 通用状态 ========================
const status = ref('pending') // pending | success | fail
const sliderX = ref(0)
const springing = ref(false)
const shaking = ref(false)
const startTime = ref(0)
const elapsed = ref('0.0')

let maxSlide = 200
let btnSize = 0
const btnHalf = computed(() => btnSize / 2)
let dragStartX = 0
let dragStartVal = 0
let trackLeft = 0

// ======================== 各模式状态 ========================
// 拼图
const puzzleTarget = ref(0)
const puzzleDeco = ref([])

// 旋转
const rotateTargetAngle = ref(0)
const rotateEmoji = ref('🏠')
const rotateCurrent = computed(() => {
	const a = rotateTargetAngle.value + (sliderX.value / Math.max(maxSlide, 1)) * 360
	return a % 360
})

// 文字点选
const orderItems = ref([])
const orderTarget = ref([])
const orderDone = ref([])
const orderWrong = ref(-1)

// 算术
const mathA = ref(0)
const mathB = ref(0)
const mathOp = ref('+')
const mathAnswer = ref(0)
const mathMax = ref(30)
const mathCurrVal = computed(() => {
	return Math.round((sliderX.value / Math.max(maxSlide, 1)) * mathMax.value)
})

// 图标点选
const iconGrid = ref([])
const iconTargetEmoji = ref('')
const iconCorrectSet = ref([])
const iconDone = ref([])
const iconWrong = ref(-1)

// ======================== 计算属性 ========================
const needSlider = computed(() => ['slide', 'puzzle', 'rotate', 'math'].includes(props.mode))

const titleText = computed(() => {
	if (props.title) return props.title
	const map = {
		slide: '安全验证', puzzle: '拼图验证', rotate: '旋转验证',
		order: '文字点选', math: '算术验证', icon: '图标点选'
	}
	return map[props.mode] || '安全验证'
})

const tipText = computed(() => {
	const map = {
		slide: '按住滑块，拖动到最右边',
		puzzle: '拖动滑块，将拼图移到缺口处',
		rotate: '拖动滑块，将图片旋转到正确角度',
		order: `请依次点击：${orderTarget.value.join(' → ')}`,
		math: '拖动滑块，选择正确答案',
		icon: `请点击所有的 ${iconTargetEmoji.value}`
	}
	return map[props.mode] || ''
})

const sliderHint = computed(() => {
	const map = {
		slide: '向右滑动到底', puzzle: '向右拖动拼合',
		rotate: '拖动调整角度', math: '滑动选择答案'
	}
	return map[props.mode] || '向右滑动'
})

const fillColor = computed(() => {
	if (status.value === 'success') return '#34C759'
	if (status.value === 'fail') return '#FF3B30'
	return '#007AFF'
})

const handleBg = computed(() => {
	if (status.value === 'success') return '#34C759'
	if (status.value === 'fail') return '#FF3B30'
	return '#FFFFFF'
})

const handleIcon = computed(() => {
	if (status.value === 'success') return '✓'
	if (status.value === 'fail') return '✗'
	return '→'
})

// ======================== 监听 show 初始化 ========================
watch(() => props.show, (val) => {
	if (val) {
		status.value = 'pending'
		sliderX.value = 0
		springing.value = false
		startTime.value = Date.now()
		nextTick(() => {
			measureTrack().then(() => {
				generateChallenge()
			})
		})
	}
})

watch(() => props.mode, () => {
	if (props.show) {
		status.value = 'pending'
		sliderX.value = 0
		nextTick(() => {
			measureTrack().then(() => {
				generateChallenge()
			})
		})
	}
})

// ======================== 轨道测量 ========================
const measureTrack = () => {
	return new Promise((resolve) => {
		if (!needSlider.value) {
			resolve()
			return
		}
		setTimeout(() => {
			const query = uni.createSelectorQuery().in(instance.proxy)
			query.select('#captchaTrack').boundingClientRect((rect) => {
				if (rect) {
					trackLeft = rect.left
					btnSize = Math.round(rect.height * 0.92)
					maxSlide = rect.width - btnSize - 4
				}
				resolve()
			}).exec()
		}, 80)
	})
}

// ======================== 生成挑战 ========================
const generateChallenge = () => {
	status.value = 'pending'
	sliderX.value = 0
	springing.value = false
	startTime.value = Date.now()

	switch (props.mode) {
		case 'puzzle': generatePuzzle(); break
		case 'rotate': generateRotate(); break
		case 'order': generateOrder(); break
		case 'math': generateMath(); break
		case 'icon': generateIcon(); break
	}
}

// --- 拼图 ---
const puzzleEmojis = ['🌸', '🌿', '🌺', '🍃', '🌷', '🍀', '🌻', '🦋', '🐝', '🌼', '☁️', '⭐']
const generatePuzzle = () => {
	puzzleTarget.value = Math.round(maxSlide * (0.3 + Math.random() * 0.5))
	const deco = []
	for (let i = 0; i < 10; i++) {
		deco.push({
			x: Math.random() * 85 + 2,
			y: Math.random() * 70 + 5,
			size: 28 + Math.floor(Math.random() * 28),
			emoji: puzzleEmojis[Math.floor(Math.random() * puzzleEmojis.length)]
		})
	}
	puzzleDeco.value = deco
}

// --- 旋转 ---
const rotateEmojiList = ['🏠', '🌲', '🚀', '⛵', '🗼', '🎸', '🦊', '🐧']
const generateRotate = () => {
	rotateTargetAngle.value = 30 + Math.floor(Math.random() * 300)
	rotateEmoji.value = rotateEmojiList[Math.floor(Math.random() * rotateEmojiList.length)]
}

// --- 文字点选 ---
const charPool = ['春', '夏', '秋', '冬', '风', '雨', '雷', '电', '山', '水', '花', '鸟', '日', '月', '星', '云', '龙', '虎']
const orderPositions = [
	{ x: 8, y: 10 }, { x: 40, y: 8 }, { x: 72, y: 12 },
	{ x: 12, y: 48 }, { x: 45, y: 50 }, { x: 76, y: 45 },
	{ x: 15, y: 82 }, { x: 50, y: 80 }, { x: 78, y: 78 }
]
const generateOrder = () => {
	const shuffled = [...charPool].sort(() => Math.random() - 0.5)
	const picked = shuffled.slice(0, 6)
	const positions = [...orderPositions].sort(() => Math.random() - 0.5).slice(0, 6)
	const items = picked.map((text, i) => ({
		text,
		x: positions[i].x + Math.floor(Math.random() * 8 - 4),
		y: positions[i].y + Math.floor(Math.random() * 6 - 3)
	}))
	orderItems.value = items
	const targetCount = 3
	const indices = items.map((_, i) => i).sort(() => Math.random() - 0.5).slice(0, targetCount)
	orderTarget.value = indices.map(i => items[i].text)
	orderDone.value = []
	orderWrong.value = -1
}

// --- 算术 ---
const generateMath = () => {
	const ops = ['+', '-', '×']
	mathOp.value = ops[Math.floor(Math.random() * ops.length)]
	mathA.value = Math.floor(Math.random() * 20) + 1
	mathB.value = Math.floor(Math.random() * 15) + 1
	if (mathOp.value === '-' && mathA.value < mathB.value) {
		const t = mathA.value; mathA.value = mathB.value; mathB.value = t
	}
	switch (mathOp.value) {
		case '+': mathAnswer.value = mathA.value + mathB.value; break
		case '-': mathAnswer.value = mathA.value - mathB.value; break
		case '×': mathAnswer.value = mathA.value * mathB.value; break
	}
	mathMax.value = Math.max(30, Math.ceil(mathAnswer.value * 1.8 / 5) * 5)
}

// --- 图标点选 ---
const emojiPool = ['🍎', '🍊', '🍋', '🍇', '🍓', '🌽', '🥕', '🍕', '🍩', '🧁', '🍔', '🌮']
const generateIcon = () => {
	const available = [...emojiPool].sort(() => Math.random() - 0.5)
	const target = available[0]
	const others = available.slice(1, 5)
	iconTargetEmoji.value = target

	const grid = []
	const correctIndices = []
	const correctCount = 3 + Math.floor(Math.random() * 2) // 3~4个
	const totalCells = 12

	// 随机放置正确图标
	const allIndices = Array.from({ length: totalCells }, (_, i) => i).sort(() => Math.random() - 0.5)
	const pickedCorrect = allIndices.slice(0, correctCount)

	for (let i = 0; i < totalCells; i++) {
		if (pickedCorrect.includes(i)) {
			grid.push({ emoji: target })
			correctIndices.push(i)
		} else {
			grid.push({ emoji: others[Math.floor(Math.random() * others.length)] })
		}
	}

	iconGrid.value = grid
	iconCorrectSet.value = correctIndices
	iconDone.value = []
	iconWrong.value = -1
}

// ======================== 滑块拖动 ========================
const onDragStart = (e) => {
	if (status.value !== 'pending') return
	dragStartX = e.touches[0].clientX
	dragStartVal = sliderX.value
	springing.value = false
}

const onDragMove = (e) => {
	if (status.value !== 'pending') return
	const dx = e.touches[0].clientX - dragStartX
	sliderX.value = Math.max(0, Math.min(maxSlide, dragStartVal + dx))
}

const onDragEnd = () => {
	if (status.value !== 'pending') return
	const ok = verifySlider()
	if (ok) {
		onSuccess()
	} else {
		onFail()
		springBack()
	}
}

// ======================== 滑块验证 ========================
const verifySlider = () => {
	switch (props.mode) {
		case 'slide':
			return sliderX.value >= maxSlide - 5
		case 'puzzle':
			return Math.abs(sliderX.value - puzzleTarget.value) <= props.tolerance
		case 'rotate': {
			const a = rotateCurrent.value % 360
			return a <= 12 || a >= 348
		}
		case 'math':
			return mathCurrVal.value === mathAnswer.value
		default:
			return false
	}
}

// ======================== 点选事件 ========================
const onOrderTap = (index) => {
	if (status.value !== 'pending') return
	if (orderDone.value.includes(index)) return

	const nextIdx = orderDone.value.length
	const expectedChar = orderTarget.value[nextIdx]
	const clickedChar = orderItems.value[index].text

	if (clickedChar === expectedChar) {
		orderDone.value = [...orderDone.value, index]
		if (orderDone.value.length === orderTarget.value.length) {
			onSuccess()
		}
	} else {
		orderWrong.value = index
		setTimeout(() => { orderWrong.value = -1 }, 500)
		onFail()
		setTimeout(() => { generateOrder() }, 800)
	}
}

const onIconTap = (index) => {
	if (status.value !== 'pending') return
	if (iconDone.value.includes(index)) return

	if (iconCorrectSet.value.includes(index)) {
		iconDone.value = [...iconDone.value, index]
		if (iconDone.value.length === iconCorrectSet.value.length) {
			onSuccess()
		}
	} else {
		iconWrong.value = index
		setTimeout(() => { iconWrong.value = -1 }, 500)
		onFail()
		setTimeout(() => { generateIcon() }, 800)
	}
}

// ======================== 结果处理 ========================
const onSuccess = () => {
	status.value = 'success'
	elapsed.value = ((Date.now() - startTime.value) / 1000).toFixed(1)
	emit('success', { mode: props.mode, elapsed: elapsed.value })
	setTimeout(() => {
		emit('update:show', false)
	}, 1500)
}

const onFail = () => {
	status.value = 'fail'
	shaking.value = true
	emit('fail', { mode: props.mode })
	setTimeout(() => {
		shaking.value = false
		if (['slide', 'puzzle', 'rotate', 'math'].includes(props.mode)) {
			status.value = 'pending'
		}
	}, 800)
}

const springBack = () => {
	springing.value = true
	sliderX.value = 0
	setTimeout(() => { springing.value = false }, 350)
}

// ======================== 公共操作 ========================
const doReset = () => {
	sliderX.value = 0
	springing.value = false
	generateChallenge()
}

const doClose = () => {
	emit('update:show', false)
	emit('close')
}

const onMaskTap = () => {
	if (props.maskClose) doClose()
}

defineExpose({ reset: doReset, open: () => emit('update:show', true), close: doClose })
</script>

<style scoped>
/* ========== 遮罩 & 弹窗 ========== */
.z-captcha {
	position: fixed;
	left: 0;
	top: 0;
	right: 0;
	bottom: 0;
	z-index: 10000;
	display: flex;
	align-items: center;
	justify-content: center;
}

.z-captcha__mask {
	position: absolute;
	left: 0;
	top: 0;
	right: 0;
	bottom: 0;
	background: rgba(0, 0, 0, 0.45);
}

.z-captcha__dialog {
	position: relative;
	width: 620rpx;
	background: #FFFFFF;
	border-radius: 28rpx;
	overflow: hidden;
	box-shadow: 0 32rpx 80rpx rgba(0, 0, 0, 0.18);
}

.z-captcha__dialog--shake {
	animation: captchaShake 0.4s ease;
}

@keyframes captchaShake {
	0%, 100% { transform: translateX(0); }
	20% { transform: translateX(-12rpx); }
	40% { transform: translateX(12rpx); }
	60% { transform: translateX(-8rpx); }
	80% { transform: translateX(8rpx); }
}

/* ========== 头部 ========== */
.z-captcha__header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 28rpx 28rpx 0;
}

.z-captcha__title {
	font-size: 32rpx;
	font-weight: 600;
	color: #1D1D1F;
}

.z-captcha__header-actions {
	display: flex;
	align-items: center;
}

.z-captcha__header-btn {
	width: 56rpx;
	height: 56rpx;
	border-radius: 50%;
	background: #F2F2F7;
	display: flex;
	align-items: center;
	justify-content: center;
	margin-left: 12rpx;
}

.z-captcha__header-btn:active {
	background: #E5E5EA;
}

.z-captcha__header-btn-text {
	font-size: 32rpx;
	color: #8E8E93;
	line-height: 1;
}

/* ========== 提示 ========== */
.z-captcha__tip {
	padding: 12rpx 28rpx 16rpx;
}

.z-captcha__tip-text {
	font-size: 24rpx;
	color: #8E8E93;
}

/* ========== 通用可视区域 ========== */
.z-captcha__visual {
	margin: 0 28rpx;
	border-radius: 20rpx;
	overflow: hidden;
	position: relative;
}

/* ========== 拼图模式 ========== */
.z-captcha__puzzle-area {
	height: 280rpx;
}

.z-captcha__puzzle-bg {
	width: 100%;
	height: 100%;
	background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
	position: relative;
}

.z-captcha__puzzle-deco {
	position: absolute;
	opacity: 0.5;
}

.z-captcha__puzzle-hole {
	position: absolute;
	top: 90rpx;
	width: 80rpx;
	height: 80rpx;
	background: rgba(0, 0, 0, 0.35);
	border: 3rpx dashed rgba(255, 255, 255, 0.8);
	border-radius: 8rpx;
}

.z-captcha__puzzle-piece {
	position: absolute;
	top: 90rpx;
	width: 80rpx;
	height: 80rpx;
	z-index: 2;
}

.z-captcha__puzzle-piece-inner {
	width: 100%;
	height: 100%;
	background: linear-gradient(135deg, #a78bfa 0%, #8b5cf6 100%);
	border-radius: 8rpx;
	border: 3rpx solid rgba(255, 255, 255, 0.9);
	box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.3);
}

/* ========== 旋转模式 ========== */
.z-captcha__rotate-area {
	height: 320rpx;
	background: #F2F2F7;
	display: flex;
	align-items: center;
	justify-content: center;
}

.z-captcha__rotate-outer {
	width: 240rpx;
	height: 240rpx;
	border-radius: 50%;
	background: #FFFFFF;
	display: flex;
	align-items: center;
	justify-content: center;
	box-shadow: 0 8rpx 32rpx rgba(0, 0, 0, 0.08);
}

.z-captcha__rotate-ring {
	width: 200rpx;
	height: 200rpx;
	border-radius: 50%;
	border: 6rpx solid #E5E5EA;
	display: flex;
	align-items: center;
	justify-content: center;
	position: relative;
	transition: none;
}

.z-captcha__rotate-dot {
	position: absolute;
	top: -8rpx;
	left: 50%;
	margin-left: -10rpx;
	width: 20rpx;
	height: 20rpx;
	border-radius: 50%;
	background: #FF3B30;
	border: 4rpx solid #FFFFFF;
}

.z-captcha__rotate-emoji {
	font-size: 80rpx;
	line-height: 1;
}

/* ========== 文字点选模式 ========== */
.z-captcha__order-area {
	height: 360rpx;
	background: linear-gradient(180deg, #EBF4FF 0%, #F0E6FF 100%);
}

.z-captcha__order-item {
	position: absolute;
	width: 72rpx;
	height: 72rpx;
	border-radius: 16rpx;
	background: #FFFFFF;
	display: flex;
	align-items: center;
	justify-content: center;
	box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.08);
}

.z-captcha__order-item:active {
	transform: scale(0.92);
}

.z-captcha__order-item--done {
	background: #34C759;
	box-shadow: 0 4rpx 12rpx rgba(52, 199, 89, 0.3);
}

.z-captcha__order-item--done .z-captcha__order-item-text {
	color: #FFFFFF;
}

.z-captcha__order-item--wrong {
	background: #FF3B30;
	animation: captchaShake 0.3s ease;
}

.z-captcha__order-item--wrong .z-captcha__order-item-text {
	color: #FFFFFF;
}

.z-captcha__order-item-text {
	font-size: 34rpx;
	font-weight: 600;
	color: #1D1D1F;
}

.z-captcha__order-seq {
	position: absolute;
	top: -12rpx;
	right: -12rpx;
	width: 32rpx;
	height: 32rpx;
	border-radius: 50%;
	background: #007AFF;
	display: flex;
	align-items: center;
	justify-content: center;
}

.z-captcha__order-seq-text {
	font-size: 20rpx;
	color: #FFFFFF;
	font-weight: 700;
}

/* ========== 算术模式 ========== */
.z-captcha__math-area {
	height: 220rpx;
	background: linear-gradient(180deg, #FFF8E1 0%, #FFF3E0 100%);
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
}

.z-captcha__math-expr {
	font-size: 52rpx;
	font-weight: 700;
	color: #1D1D1F;
	letter-spacing: 4rpx;
}

.z-captcha__math-val {
	font-size: 72rpx;
	font-weight: 800;
	color: #FF9500;
	margin-top: 8rpx;
	transition: color 0.15s ease;
}

.z-captcha__math-val--match {
	color: #34C759;
}

/* ========== 图标点选模式 ========== */
.z-captcha__icon-area {
	background: #F2F2F7;
	padding: 16rpx;
}

.z-captcha__icon-grid {
	display: flex;
	flex-wrap: wrap;
	justify-content: space-between;
}

.z-captcha__icon-cell {
	width: 23.5%;
	height: 120rpx;
	background: #FFFFFF;
	border-radius: 16rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	margin-bottom: 12rpx;
	box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.04);
}

.z-captcha__icon-cell:active {
	transform: scale(0.93);
}

.z-captcha__icon-cell--done {
	background: #E8F5E9;
	border: 3rpx solid #34C759;
}

.z-captcha__icon-cell--wrong {
	background: #FFEBEE;
	border: 3rpx solid #FF3B30;
	animation: captchaShake 0.3s ease;
}

.z-captcha__icon-cell-text {
	font-size: 48rpx;
}

/* ========== 滑块轨道 ========== */
.z-captcha__slider-box {
	padding: 24rpx 28rpx 28rpx;
}

.z-captcha__track {
	position: relative;
	width: 100%;
	height: 80rpx;
	background: #F2F2F7;
	border-radius: 40rpx;
	overflow: visible;
}

.z-captcha__track-fill {
	position: absolute;
	left: 0;
	top: 0;
	height: 100%;
	border-radius: 40rpx;
	background: #007AFF;
	opacity: 0.15;
	transition: background 0.2s ease;
}

.z-captcha__track-hint {
	position: absolute;
	left: 0;
	right: 0;
	top: 0;
	bottom: 0;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 24rpx;
	color: #AEAEB2;
	pointer-events: none;
}

.z-captcha__handle {
	position: absolute;
	top: 4rpx;
	width: 72rpx;
	height: 72rpx;
	border-radius: 50%;
	background: #FFFFFF;
	display: flex;
	align-items: center;
	justify-content: center;
	box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.12);
	z-index: 2;
}

.z-captcha__handle--spring {
	transition: left 0.35s cubic-bezier(0.36, 0.66, 0.04, 1);
}

.z-captcha__handle-icon {
	font-size: 32rpx;
	color: #007AFF;
	font-weight: 700;
}

/* ========== 算术范围标签 ========== */
.z-captcha__math-labels {
	display: flex;
	justify-content: space-between;
	padding: 8rpx 8rpx 0;
}

.z-captcha__math-label {
	font-size: 22rpx;
	color: #AEAEB2;
}

/* ========== 结果蒙层 ========== */
.z-captcha__result {
	position: absolute;
	left: 0;
	right: 0;
	top: 0;
	bottom: 0;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	z-index: 10;
	border-radius: 28rpx;
}

.z-captcha__result--success {
	background: rgba(52, 199, 89, 0.92);
}

.z-captcha__result--fail {
	background: rgba(255, 59, 48, 0.88);
}

.z-captcha__result-icon {
	font-size: 80rpx;
	color: #FFFFFF;
	font-weight: 700;
}

.z-captcha__result-text {
	font-size: 30rpx;
	color: #FFFFFF;
	font-weight: 600;
	margin-top: 8rpx;
}

.z-captcha__result-time {
	font-size: 24rpx;
	color: rgba(255, 255, 255, 0.8);
	margin-top: 4rpx;
}
</style>
