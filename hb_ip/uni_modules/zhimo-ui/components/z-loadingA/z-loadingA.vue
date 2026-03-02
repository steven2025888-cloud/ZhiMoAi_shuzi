<template>
	<view 
		class="z-loading" 
		:class="{ 'z-loading--fixed': fixed }"
		:style="containerStyle"
	>
		<!-- 类型1: 弹跳圆点 -->
		<view v-if="type === 1" class="z-loading__bounce">
			<view 
				v-for="i in 3" 
				:key="i"
				class="z-loading__bounce-dot"
				:class="[`z-loading__bounce-dot--${i}`]"
				:style="dotStyle"
			/>
		</view>

		<!-- 类型2: 音频条 -->
		<view v-else-if="type === 2" class="z-loading__bars">
			<view 
				v-for="i in 3" 
				:key="i"
				class="z-loading__bar"
				:class="[`z-loading__bar--${i}`]"
				:style="barStyle"
			/>
		</view>

		<!-- 类型3: 旋转圆环 -->
		<view
			v-else-if="type === 3"
			class="z-loading__ring"
			:class="{ 'z-loading__ring--gradient': isGradient }"
			:style="ringStyle"
		/>

		<!-- 类型4: 轨道旋转 -->
		<view v-else-if="type === 4" class="z-loading__orbit" :style="orbitStyle">
			<view class="z-loading__orbit-dot" :style="orbitDotStyle" />
		</view>

		<!-- 类型5: 脉冲圆点 -->
		<view v-else-if="type === 5" class="z-loading__pulse">
			<view 
				v-for="i in 3" 
				:key="i"
				class="z-loading__pulse-dot"
				:class="[`z-loading__pulse-dot--${i}`]"
				:style="dotStyle"
			/>
		</view>

		<!-- 类型6: 旋转方块 -->
		<view 
			v-else-if="type === 6" 
			class="z-loading__square"
			:style="squareStyle"
		/>

		<!-- 类型7: 双圆环 -->
		<view v-else-if="type === 7" class="z-loading__dual-ring">
			<view class="z-loading__dual-ring-inner" :style="dualRingStyle" />
			<view class="z-loading__dual-ring-outer" :style="dualRingOuterStyle" />
		</view>

		<!-- 类型8: 波浪圆点 -->
		<view v-else-if="type === 8" class="z-loading__wave">
			<view 
				v-for="i in 5" 
				:key="i"
				class="z-loading__wave-dot"
				:class="[`z-loading__wave-dot--${i}`]"
				:style="waveDotStyle"
			/>
		</view>

		<!-- 类型9: 渐变旋转 -->
		<view 
			v-else-if="type === 9" 
			class="z-loading__gradient"
			:style="gradientStyle"
		/>

		<!-- 类型10: 心跳 -->
		<view v-else-if="type === 10" class="z-loading__heartbeat">
			<view class="z-loading__heart" :style="heartStyle">
				<view class="z-loading__heart-before" :style="heartBeforeStyle" />
				<view class="z-loading__heart-after" :style="heartAfterStyle" />
			</view>
		</view>
	</view>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
	// 加载动画类型 1-10
	type: {
		type: Number,
		default: 1,
		validator: (val) => val >= 1 && val <= 10
	},
	// 主题颜色
	color: {
		type: String,
		default: '#6366f1'
	},
	// 尺寸 small/medium/large 或具体数值
	size: {
		type: [String, Number],
		default: 'medium'
	},
	// 是否固定在屏幕中央
	fixed: {
		type: Boolean,
		default: false
	},
	// 遮罩背景色 (fixed为true时有效)
	maskColor: {
		type: String,
		default: 'rgba(255, 255, 255, 0.9)'
	}
})

// 检测是否为渐变色
const isGradient = computed(() => {
	return props.color.includes('gradient')
})

// 计算尺寸
const sizeValue = computed(() => {
	const sizeMap = {
		small: 24,
		medium: 36,
		large: 48
	}
	if (typeof props.size === 'number') {
		return props.size
	}
	return sizeMap[props.size] || 36
})

// 容器样式
const containerStyle = computed(() => {
	const style = {}
	if (props.fixed) {
		style.background = props.maskColor
	}
	return style
})

// 圆点样式
const dotStyle = computed(() => ({
	width: `${sizeValue.value * 0.4}rpx`,
	height: `${sizeValue.value * 0.4}rpx`,
	background: props.color
}))

// 条形样式
const barStyle = computed(() => ({
	width: `${sizeValue.value * 0.2}rpx`,
	background: props.color
}))

// 圆环样式
const ringStyle = computed(() => {
	const style = {
		width: `${sizeValue.value}rpx`,
		height: `${sizeValue.value}rpx`
	}

	// 如果是渐变色，使用background
	if (isGradient.value) {
		style.background = props.color
	} else {
		// 如果是纯色，使用border
		style.borderLeftColor = props.color
		style.borderRightColor = props.color
	}

	return style
})

// 轨道样式
const orbitStyle = computed(() => ({
	width: `${sizeValue.value * 1.4}rpx`,
	height: `${sizeValue.value * 1.4}rpx`,
	borderColor: props.color
}))

// 轨道圆点样式
const orbitDotStyle = computed(() => ({
	width: `${sizeValue.value * 0.4}rpx`,
	height: `${sizeValue.value * 0.4}rpx`,
	background: props.color
}))

// 方块样式
const squareStyle = computed(() => ({
	width: `${sizeValue.value * 0.8}rpx`,
	height: `${sizeValue.value * 0.8}rpx`,
	background: props.color
}))

// 双圆环样式
const dualRingStyle = computed(() => ({
	width: `${sizeValue.value * 0.6}rpx`,
	height: `${sizeValue.value * 0.6}rpx`,
	borderTopColor: props.color,
	borderBottomColor: props.color
}))

const dualRingOuterStyle = computed(() => ({
	width: `${sizeValue.value}rpx`,
	height: `${sizeValue.value}rpx`,
	borderLeftColor: props.color,
	borderRightColor: props.color
}))

// 波浪圆点样式
const waveDotStyle = computed(() => ({
	width: `${sizeValue.value * 0.25}rpx`,
	height: `${sizeValue.value * 0.25}rpx`,
	background: props.color
}))

// 渐变旋转样式
const gradientStyle = computed(() => ({
	width: `${sizeValue.value}rpx`,
	height: `${sizeValue.value}rpx`,
	background: `conic-gradient(from 0deg, transparent, ${props.color})`
}))

// 心跳样式
const heartStyle = computed(() => ({
	width: `${sizeValue.value * 0.8}rpx`,
	height: `${sizeValue.value * 0.8}rpx`
}))

const heartBeforeStyle = computed(() => ({
	background: props.color
}))

const heartAfterStyle = computed(() => ({
	background: props.color
}))
</script>

<style scoped>
.z-loading {
	display: flex;
	align-items: center;
	justify-content: center;
	padding: 20rpx;
}

.z-loading--fixed {
	position: fixed;
	left: 0;
	right: 0;
	top: 0;
	bottom: 0;
	z-index: 9999;
}

/* 类型1: 弹跳圆点 */
.z-loading__bounce {
	display: flex;
	align-items: center;
	gap: 8rpx;
}

.z-loading__bounce-dot {
	border-radius: 50%;
	animation: bounce 1.4s ease-in-out infinite both;
}

.z-loading__bounce-dot--1 {
	animation-delay: -0.32s;
}

.z-loading__bounce-dot--2 {
	animation-delay: -0.16s;
}

.z-loading__bounce-dot--3 {
	animation-delay: 0s;
}

@keyframes bounce {
	0%, 80%, 100% {
		transform: scale(0);
		opacity: 0.5;
	}
	40% {
		transform: scale(1);
		opacity: 1;
	}
}

/* 类型2: 音频条 */
.z-loading__bars {
	display: flex;
	align-items: flex-end;
	height: 60rpx;
	gap: 6rpx;
}

.z-loading__bar {
	border-radius: 4rpx 4rpx 0 0;
	animation: bars 0.6s ease-in-out infinite alternate;
}

.z-loading__bar--1 {
	animation-delay: 0s;
}

.z-loading__bar--2 {
	animation-delay: 0.2s;
}

.z-loading__bar--3 {
	animation-delay: 0.4s;
}

@keyframes bars {
	0% {
		height: 20%;
	}
	100% {
		height: 100%;
	}
}

/* 类型3: 旋转圆环 */
.z-loading__ring {
	border: 3px solid transparent;
	border-radius: 50%;
	animation: spin 0.9s linear infinite;
}

/* 渐变色圆环 - 使用遮罩实现 */
.z-loading__ring--gradient {
	border: none;
	position: relative;
}

.z-loading__ring--gradient::before {
	content: '';
	position: absolute;
	inset: 0;
	border-radius: 50%;
	padding: 3px;
	background: inherit;
	-webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
	-webkit-mask-composite: xor;
	mask-composite: exclude;
}

@keyframes spin {
	0% {
		transform: rotate(0deg);
	}
	100% {
		transform: rotate(360deg);
	}
}

/* 类型4: 轨道旋转 */
.z-loading__orbit {
	border: 2rpx solid;
	border-radius: 50%;
	position: relative;
	animation: spin 1s linear infinite;
	opacity: 0.3;
}

.z-loading__orbit-dot {
	position: absolute;
	top: -8rpx;
	left: 50%;
	transform: translateX(-50%);
	border-radius: 50%;
	opacity: 1;
}

/* 类型5: 脉冲圆点 */
.z-loading__pulse {
	display: flex;
	align-items: center;
	gap: 16rpx;
}

.z-loading__pulse-dot {
	border-radius: 50%;
	animation: pulse 1.2s ease-in-out infinite;
}

.z-loading__pulse-dot--1 {
	animation-delay: 0s;
}

.z-loading__pulse-dot--2 {
	animation-delay: 0.4s;
}

.z-loading__pulse-dot--3 {
	animation-delay: 0.8s;
}

@keyframes pulse {
	0%, 100% {
		opacity: 0.25;
		transform: scale(0.8);
	}
	50% {
		opacity: 1;
		transform: scale(1);
	}
}

/* 类型6: 旋转方块 */
.z-loading__square {
	border-radius: 4rpx;
	animation: square 1.2s ease-in-out infinite;
}

@keyframes square {
	0% {
		transform: rotate(0deg) scale(1);
	}
	25% {
		transform: rotate(90deg) scale(0.8);
	}
	50% {
		transform: rotate(180deg) scale(1);
	}
	75% {
		transform: rotate(270deg) scale(0.8);
	}
	100% {
		transform: rotate(360deg) scale(1);
	}
}

/* 类型7: 双圆环 */
.z-loading__dual-ring {
	position: relative;
	display: flex;
	align-items: center;
	justify-content: center;
}

.z-loading__dual-ring-inner {
	position: absolute;
	border: 3px solid transparent;
	border-radius: 50%;
	animation: spin 0.8s linear infinite reverse;
}

.z-loading__dual-ring-outer {
	border: 3px solid transparent;
	border-radius: 50%;
	animation: spin 1s linear infinite;
}

/* 类型8: 波浪圆点 */
.z-loading__wave {
	display: flex;
	align-items: center;
	gap: 6rpx;
}

.z-loading__wave-dot {
	border-radius: 50%;
	animation: wave 1s ease-in-out infinite;
}

.z-loading__wave-dot--1 {
	animation-delay: 0s;
}

.z-loading__wave-dot--2 {
	animation-delay: 0.1s;
}

.z-loading__wave-dot--3 {
	animation-delay: 0.2s;
}

.z-loading__wave-dot--4 {
	animation-delay: 0.3s;
}

.z-loading__wave-dot--5 {
	animation-delay: 0.4s;
}

@keyframes wave {
	0%, 100% {
		transform: translateY(0);
		opacity: 0.5;
	}
	50% {
		transform: translateY(-16rpx);
		opacity: 1;
	}
}

/* 类型9: 渐变旋转 */
.z-loading__gradient {
	border-radius: 50%;
	animation: spin 1s linear infinite;
	position: relative;
}

.z-loading__gradient::before {
	content: '';
	position: absolute;
	top: 4rpx;
	left: 4rpx;
	right: 4rpx;
	bottom: 4rpx;
	background: #fff;
	border-radius: 50%;
}

/* 类型10: 心跳 */
.z-loading__heartbeat {
	display: flex;
	align-items: center;
	justify-content: center;
}

.z-loading__heart {
	position: relative;
	animation: heartbeat 1s ease-in-out infinite;
	transform: rotate(-45deg);
}

.z-loading__heart-before,
.z-loading__heart-after {
	position: absolute;
	width: 100%;
	height: 100%;
	border-radius: 50%;
}

.z-loading__heart-before {
	top: -50%;
	left: 0;
}

.z-loading__heart-after {
	top: 0;
	left: 50%;
}

@keyframes heartbeat {
	0%, 100% {
		transform: rotate(-45deg) scale(0.8);
	}
	50% {
		transform: rotate(-45deg) scale(1.1);
	}
}
</style>
