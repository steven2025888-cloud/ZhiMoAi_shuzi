<template>
	<view 
		class="z-spin" 
		:class="[
			paused ? 'z-spin--paused' : '',
			`z-spin--${direction}`
		]"
		:style="spinStyle"
		ref="spinRef"
	>
		<slot></slot>
	</view>
</template>

<script setup>
/**
 * z-spin 旋转动画
 * @description 让任意元素进行旋转动画
 * @property {Number|String} width 宽度，单位rpx，0为auto
 * @property {Number|String} height 高度，单位rpx，0为auto
 * @property {Number} duration 动画时长，单位ms
 * @property {String} timing 动画曲线 linear/ease/ease-in/ease-out/ease-in-out
 * @property {Boolean} paused 是否暂停动画
 * @property {String} direction 旋转方向 normal/reverse
 * @example <z-spin><view>旋转内容</view></z-spin>
 */
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
	// 宽度，单位rpx，0为auto
	width: {
		type: [Number, String],
		default: 0
	},
	// 高度，单位rpx，0为auto
	height: {
		type: [Number, String],
		default: 0
	},
	// 动画时长，单位ms
	duration: {
		type: Number,
		default: 850
	},
	// 动画曲线
	timing: {
		type: String,
		default: 'linear',
		validator: (val) => ['linear', 'ease', 'ease-in', 'ease-out', 'ease-in-out'].includes(val)
	},
	// 是否暂停
	paused: {
		type: Boolean,
		default: false
	},
	// 旋转方向 normal正向 reverse反向
	direction: {
		type: String,
		default: 'normal',
		validator: (val) => ['normal', 'reverse'].includes(val)
	}
})

const spinRef = ref(null)

// #ifdef APP-NVUE
const animation = uni.requireNativePlugin('animation')
let deg = 0
let stopped = false

const runAnimation = () => {
	if (!spinRef.value || stopped || props.paused) return
	
	const targetDeg = props.direction === 'reverse' ? deg - 360 : deg + 360
	
	animation.transition(
		spinRef.value.ref,
		{
			styles: {
				transform: `rotate(${targetDeg}deg)`
			},
			duration: props.duration,
			timingFunction: props.timing,
			needLayout: false,
			delay: 0
		},
		() => {
			deg = targetDeg
			runAnimation()
		}
	)
}

onMounted(() => {
	nextTick(() => {
		setTimeout(() => {
			runAnimation()
		}, 50)
	})
})

onBeforeUnmount(() => {
	stopped = true
	deg = 0
})
// #endif

// 计算样式
const spinStyle = computed(() => {
	const style = {}
	
	if (props.width) {
		style.width = `${props.width}rpx`
	}
	
	if (props.height) {
		style.height = `${props.height}rpx`
	}
	
	// #ifndef APP-NVUE
	style.animationDuration = `${props.duration}ms`
	style.animationTimingFunction = props.timing
	// #endif
	
	return style
})
</script>

<style scoped>
.z-spin {
	/* #ifndef APP-NVUE */
	display: inline-flex;
	animation: z-spin-rotate 0.85s linear infinite;
	/* #endif */
	align-items: center;
	justify-content: center;
	flex-direction: row;
}

.z-spin--paused {
	/* #ifndef APP-NVUE */
	animation-play-state: paused;
	/* #endif */
}

.z-spin--reverse {
	/* #ifndef APP-NVUE */
	animation-direction: reverse;
	/* #endif */
}

/* #ifndef APP-NVUE */
@keyframes z-spin-rotate {
	from {
		transform: rotate(0deg);
	}
	to {
		transform: rotate(360deg);
	}
}
/* #endif */
</style>
