<template>
	<view class="z-sort-item" :style="cellStyle">
		<view class="z-sort-item__box" :style="boxStyle">
			<!-- 网格模式 -->
			<view v-if="mode === 'grid'" class="z-sort-item__grid">
				<image v-if="validImage" class="z-sort-item__img" :src="image" :style="imgStyle" mode="aspectFill"
					:draggable="false" />
				<view v-if="showDelete" class="z-sort-item__close" @tap.stop="onDelete">
					<view class="z-sort-item__close-bg">
						<view class="z-sort-item__cross z-sort-item__cross--a"></view>
						<view class="z-sort-item__cross z-sort-item__cross--b"></view>
					</view>
				</view>
			</view>
			<!-- 列表模式 -->
			<view v-else class="z-sort-item__row">
				<view v-if="showDelete" class="z-sort-item__remove" @tap.stop="onDelete">
					<view class="z-sort-item__remove-dot">
						<view class="z-sort-item__remove-bar"></view>
					</view>
				</view>
				<text class="z-sort-item__label" :style="labelStyle">{{ label }}</text>
				<view v-if="showHandle" class="z-sort-item__grip">
					<view class="z-sort-item__grip-line"></view>
					<view class="z-sort-item__grip-line"></view>
					<view class="z-sort-item__grip-line"></view>
				</view>
			</view>
		</view>
	</view>
</template>

<script>
import { defineComponent, computed } from 'vue'
export default defineComponent({
	name: 'z-drag-sort-item',
	emits: ['delete'],
	props: {
		width: { type: Number, default: 100 },
		height: { type: Number, default: 100 },
		image: { type: String, default: '' },
		label: { type: String, default: '' },
		mode: { type: String, default: 'grid' },
		showDelete: { type: Boolean, default: false },
		showHandle: { type: Boolean, default: true },
		index: { type: [Number, String], default: 0 },
		padding: { type: Number, default: 6 },
		background: { type: String, default: '#ffffff' },
		radius: { type: [Number, String], default: 8 },
		fontSize: { type: [Number, String], default: 30 },
		textColor: { type: String, default: '#333333' }
	},
	setup(props, { emit }) {
		const validImage = computed(() => props.image && props.image !== '' && props.image !== 'true')
		const cellStyle = computed(() => ({ width: props.width + 'px', height: props.height + 'px' }))
		const boxStyle = computed(() => {
			const w = props.width - props.padding * 2
			const h = props.height - props.padding * 2
			return {
				width: w + 'px', height: h + 'px',
				background: props.background, borderRadius: props.radius + 'rpx', overflow: 'hidden',
				justifyContent: props.mode === 'list' ? 'space-between' : 'center'
			}
		})
		const imgStyle = computed(() => {
			const s = Math.min(props.width, props.height) - props.padding * 2
			return { width: s + 'px', height: s + 'px', borderRadius: props.radius + 'rpx' }
		})
		const labelStyle = computed(() => ({ fontSize: props.fontSize + 'rpx', color: props.textColor }))
		const onDelete = () => emit('delete', { index: Number(props.index) })
		return { validImage, cellStyle, boxStyle, imgStyle, labelStyle, onDelete }
	}
})
</script>

<style scoped>
.z-sort-item {
	/* #ifndef APP-NVUE */
	display: flex;
	box-sizing: border-box;
	/* #endif */
	justify-content: center;
	align-items: center;
}
.z-sort-item__box {
	/* #ifndef APP-NVUE */
	display: flex;
	box-sizing: border-box;
	/* #endif */
	flex-direction: row;
	align-items: center;
	position: relative;
}
.z-sort-item__grid {
	flex: 1;
	/* #ifndef APP-NVUE */
	display: flex;
	/* #endif */
	align-items: center;
	justify-content: center;
	position: relative;
}
.z-sort-item__img {
	/* #ifndef APP-NVUE */
	display: block;
	pointer-events: none;
	flex-shrink: 0;
	/* #endif */
}
.z-sort-item__close {
	position: absolute;
	right: 4rpx;
	top: 4rpx;
	/* #ifndef APP-NVUE */
	z-index: 3;
	flex-shrink: 0;
	/* #endif */
}
.z-sort-item__close-bg {
	width: 36rpx;
	height: 36rpx;
	border-radius: 18rpx;
	background-color: rgba(0, 0, 0, 0.45);
	/* #ifndef APP-NVUE */
	display: flex;
	/* #endif */
	align-items: center;
	justify-content: center;
	position: relative;
}
.z-sort-item__cross {
	position: absolute;
	width: 18rpx;
	height: 3rpx;
	background-color: #ffffff;
	border-radius: 2rpx;
}
.z-sort-item__cross--a { transform: rotate(45deg); }
.z-sort-item__cross--b { transform: rotate(-45deg); }
.z-sort-item__row {
	flex: 1;
	/* #ifndef APP-NVUE */
	display: flex;
	/* #endif */
	flex-direction: row;
	align-items: center;
	padding: 0 24rpx;
	position: relative;
}
/* #ifndef APP-NVUE */
.z-sort-item__row::after {
	content: '';
	position: absolute;
	left: 24rpx;
	right: 0;
	bottom: 0;
	border-bottom: 1px solid #eeeeee;
	transform: scaleY(0.5) translateZ(0);
	transform-origin: 0 100%;
}
/* #endif */
/* #ifdef APP-NVUE */
.z-sort-item__row {
	border-bottom-width: 0.5px;
	border-bottom-style: solid;
	border-bottom-color: #eeeeee;
}
/* #endif */
.z-sort-item__remove {
	margin-right: 20rpx;
	/* #ifndef APP-NVUE */
	flex-shrink: 0;
	/* #endif */
}
.z-sort-item__remove-dot {
	width: 40rpx;
	height: 40rpx;
	border-radius: 20rpx;
	background-color: #ff4d4f;
	/* #ifndef APP-NVUE */
	display: flex;
	/* #endif */
	align-items: center;
	justify-content: center;
}
.z-sort-item__remove-bar {
	width: 18rpx;
	height: 3rpx;
	background-color: #ffffff;
	border-radius: 2rpx;
}
.z-sort-item__label {
	flex: 1;
	font-size: 30rpx;
	/* #ifdef APP-NVUE */
	lines: 1;
	/* #endif */
	/* #ifndef APP-NVUE */
	white-space: nowrap;
	overflow: hidden;
	/* #endif */
	text-overflow: ellipsis;
}
.z-sort-item__grip {
	margin-left: 16rpx;
	padding: 8rpx 0;
	/* #ifndef APP-NVUE */
	flex-shrink: 0;
	display: flex;
	/* #endif */
	flex-direction: column;
	align-items: center;
	justify-content: center;
}
.z-sort-item__grip-line {
	width: 32rpx;
	height: 3rpx;
	background-color: #cccccc;
	border-radius: 2rpx;
	margin: 4rpx 0;
}
</style>
