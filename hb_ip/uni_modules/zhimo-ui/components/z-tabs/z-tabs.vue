<template>
	<view 
		class="z-tabs"
		:class="[
			`z-tabs--${type}`,
			{ 'z-tabs--disabled': disabled },
			{ 'z-tabs--scrollable': scrollable }
		]"
		:style="tabsStyle"
	>
		<scroll-view 
			v-if="scrollable"
			class="z-tabs__scroll"
			scroll-x
			:scroll-left="scrollLeft"
			scroll-with-animation
		>
			<view class="z-tabs__wrapper" :style="wrapperStyle">
				<view 
					v-for="(item, index) in normalizedItems"
					:key="index"
					class="z-tabs__item"
					:class="[
						{ 'z-tabs__item--active': modelValue === index },
						{ 'z-tabs__item--disabled': item.disabled }
					]"
					:style="getItemStyle(index)"
					@click="handleClick(index)"
				>
					<!-- 图标 -->
					<z-icon 
						v-if="item.icon"
						:name="item.icon"
						:size="iconSize"
						:color="modelValue === index ? activeIconColor : iconColor"
						class="z-tabs__icon"
					/>
					<!-- 徽标 -->
					<view v-if="item.badge" class="z-tabs__badge">
						<text class="z-tabs__badge-text">{{ item.badge > 99 ? '99+' : item.badge }}</text>
					</view>
					<!-- 红点 -->
					<view v-else-if="item.dot" class="z-tabs__dot" />
					<!-- 文本 -->
					<text 
						class="z-tabs__text"
						:style="getTextStyle(index)"
					>{{ item.label }}</text>
				</view>
				<!-- 滑块指示器（仅 line/card 类型） -->
				<view 
					v-if="type === 'line' || type === 'card'"
					class="z-tabs__indicator"
					:style="indicatorStyle"
				/>
			</view>
		</scroll-view>
		
		<view v-else class="z-tabs__wrapper" :style="wrapperStyle">
			<view 
				v-for="(item, index) in normalizedItems"
				:key="index"
				class="z-tabs__item"
				:class="[
					{ 'z-tabs__item--active': modelValue === index },
					{ 'z-tabs__item--disabled': item.disabled }
				]"
				:style="getItemStyle(index)"
				@click="handleClick(index)"
			>
				<!-- 图标 -->
				<z-icon 
					v-if="item.icon"
					:name="item.icon"
					:size="iconSize"
					:color="modelValue === index ? activeIconColor : iconColor"
					class="z-tabs__icon"
				/>
				<!-- 徽标 -->
				<view v-if="item.badge" class="z-tabs__badge">
					<text class="z-tabs__badge-text">{{ item.badge > 99 ? '99+' : item.badge }}</text>
				</view>
				<!-- 红点 -->
				<view v-else-if="item.dot" class="z-tabs__dot" />
				<!-- 文本 -->
				<text 
					class="z-tabs__text"
					:style="getTextStyle(index)"
				>{{ item.label }}</text>
			</view>
			<!-- 滑块指示器（仅 line/card 类型） -->
			<view 
				v-if="type === 'line' || type === 'card'"
				class="z-tabs__indicator"
				:style="indicatorStyle"
			/>
		</view>
	</view>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
	// 当前选中项索引
	modelValue: {
		type: Number,
		default: 0
	},
	// 标签项列表
	items: {
		type: Array,
		default: () => []
	},
	// 标签项字段名
	labelKey: {
		type: String,
		default: 'label'
	},
	// 禁用字段名
	disabledKey: {
		type: String,
		default: 'disabled'
	},
	// 类型：button / line / card / pill
	type: {
		type: String,
		default: 'button'
	},
	// 主题色
	color: {
		type: String,
		default: '#6366f1'
	},
	// 未选中文字颜色
	textColor: {
		type: String,
		default: '#64748b'
	},
	// 选中文字颜色
	activeColor: {
		type: String,
		default: ''
	},
	// 背景色
	background: {
		type: String,
		default: ''
	},
	// 选中项背景色
	activeBackground: {
		type: String,
		default: ''
	},
	// 高度
	height: {
		type: [Number, String],
		default: 72
	},
	// 字体大小
	fontSize: {
		type: [Number, String],
		default: 28
	},
	// 选中时是否加粗
	bold: {
		type: Boolean,
		default: true
	},
	// 圆角
	radius: {
		type: [Number, String],
		default: 8
	},
	// 图标大小
	iconSize: {
		type: [Number, String],
		default: 36
	},
	// 图标颜色
	iconColor: {
		type: String,
		default: '#94a3b8'
	},
	// 选中图标颜色
	activeIconColor: {
		type: String,
		default: ''
	},
	// 是否禁用
	disabled: {
		type: Boolean,
		default: false
	},
	// 是否可滚动
	scrollable: {
		type: Boolean,
		default: false
	},
	// 是否等宽
	equalWidth: {
		type: Boolean,
		default: true
	},
	// 外边距
	margin: {
		type: Array,
		default: () => []
	},
	// 内边距
	padding: {
		type: Array,
		default: () => []
	},
	// 指示器宽度（line类型）
	indicatorWidth: {
		type: [Number, String],
		default: 40
	},
	// 指示器高度（line类型）
	indicatorHeight: {
		type: [Number, String],
		default: 4
	},
	// 是否显示边框（button类型）
	border: {
		type: Boolean,
		default: true
	},
	// 动画时长
	duration: {
		type: Number,
		default: 300
	}
})

const emit = defineEmits(['update:modelValue', 'change'])

// 滚动位置
const scrollLeft = ref(0)

// 规范化标签项
const normalizedItems = computed(() => {
	return props.items.map(item => {
		if (typeof item === 'string') {
			return { label: item }
		}
		return {
			label: item[props.labelKey] || item.name || item.label || item.text || '',
			disabled: item[props.disabledKey] || item.disabled || false,
			icon: item.icon || '',
			badge: item.badge || 0,
			dot: item.dot || false,
			...item
		}
	})
})

// 计算颜色
const computedActiveColor = computed(() => {
	if (props.activeColor) return props.activeColor
	if (props.type === 'button') return '#ffffff'
	return props.color
})

const computedActiveIconColor = computed(() => {
	return props.activeIconColor || computedActiveColor.value
})

// 容器样式
const tabsStyle = computed(() => {
	const style = {}
	const margin = props.margin
	if (margin.length) {
		style.marginTop = margin[0] || 0
		style.marginRight = margin[1] || 0
		style.marginBottom = margin[2] || margin[0] || 0
		style.marginLeft = margin[3] || margin[1] || 0
	}
	return style
})

// 包装器样式
const wrapperStyle = computed(() => {
	const style = {
		height: `${props.height}rpx`
	}
	
	const padding = props.padding
	if (padding.length) {
		style.paddingTop = padding[0] || 0
		style.paddingRight = padding[1] || 0
		style.paddingBottom = padding[2] || padding[0] || 0
		style.paddingLeft = padding[3] || padding[1] || 0
	}
	
	// 背景和边框样式
	if (props.type === 'button') {
		if (props.border) {
			style.borderColor = props.color
		}
		style.borderRadius = `${props.radius}rpx`
	} else if (props.type === 'pill') {
		style.background = props.background || '#f1f5f9'
		style.borderRadius = `${props.radius}rpx`
		style.padding = '6rpx'
	} else if (props.type === 'card') {
		style.background = props.background || '#f8fafc'
		style.borderRadius = `${props.radius}rpx`
	}
	
	return style
})

// 单项样式
const getItemStyle = (index) => {
	const style = {}
	const isActive = props.modelValue === index
	const isFirst = index === 0
	const isLast = index === normalizedItems.value.length - 1
	
	if (props.type === 'button') {
		// 按钮类型
		if (props.border) {
			style.borderColor = props.color
			if (isFirst) {
				style.borderTopLeftRadius = `${props.radius}rpx`
				style.borderBottomLeftRadius = `${props.radius}rpx`
			}
			if (isLast) {
				style.borderTopRightRadius = `${props.radius}rpx`
				style.borderBottomRightRadius = `${props.radius}rpx`
			}
		}
		if (isActive) {
			style.background = props.activeBackground || props.color
		}
	} else if (props.type === 'pill') {
		// 药丸类型
		style.borderRadius = `${props.radius - 6}rpx`
		if (isActive) {
			style.background = props.activeBackground || '#ffffff'
			style.boxShadow = '0 2rpx 8rpx rgba(0, 0, 0, 0.08)'
		}
	}
	
	if (!props.equalWidth && props.scrollable) {
		style.flex = 'none'
		style.paddingLeft = '32rpx'
		style.paddingRight = '32rpx'
	}
	
	return style
}

// 文字样式
const getTextStyle = (index) => {
	const isActive = props.modelValue === index
	return {
		fontSize: `${props.fontSize}rpx`,
		color: isActive ? computedActiveColor.value : props.textColor,
		fontWeight: props.bold && isActive ? '600' : '400'
	}
}

// 指示器样式
const indicatorStyle = computed(() => {
	const count = normalizedItems.value.length
	if (count === 0) return {}
	
	const itemWidth = 100 / count
	const left = props.modelValue * itemWidth + (itemWidth / 2)
	
	const style = {
		width: `${props.indicatorWidth}rpx`,
		height: `${props.indicatorHeight}rpx`,
		left: `${left}%`,
		transform: 'translateX(-50%)',
		background: props.color,
		transition: `left ${props.duration}ms cubic-bezier(0.4, 0, 0.2, 1)`
	}
	
	if (props.type === 'card') {
		style.bottom = '0'
		style.borderRadius = `${props.indicatorHeight}rpx`
	} else {
		style.bottom = '0'
		style.borderRadius = `${props.indicatorHeight}rpx`
	}
	
	return style
})

// 点击处理
const handleClick = (index) => {
	const item = normalizedItems.value[index]
	if (props.disabled || item.disabled) return
	if (props.modelValue === index) return
	
	emit('update:modelValue', index)
	emit('change', { index, item })
}

// 暴露方法
defineExpose({
	setIndex: (index) => {
		if (index >= 0 && index < normalizedItems.value.length) {
			emit('update:modelValue', index)
		}
	}
})
</script>

<style scoped>
.z-tabs {
	width: 100%;
}

.z-tabs--disabled {
	opacity: 0.5;
	pointer-events: none;
}

.z-tabs__scroll {
	width: 100%;
}

.z-tabs__wrapper {
	display: flex;
	flex-direction: row;
	align-items: center;
	position: relative;
	box-sizing: border-box;
}

/* 按钮类型边框 */
.z-tabs--button .z-tabs__wrapper {
	border-width: 2rpx;
	border-style: solid;
	border-color: transparent;
}

/* 标签项 */
.z-tabs__item {
	flex: 1;
	display: flex;
	flex-direction: row;
	align-items: center;
	justify-content: center;
	height: 100%;
	position: relative;
	transition: all 0.3s ease;
	box-sizing: border-box;
}

/* 按钮类型边框 */
.z-tabs--button .z-tabs__item {
	border-right-width: 2rpx;
	border-right-style: solid;
}

.z-tabs--button .z-tabs__item:last-child {
	border-right-width: 0;
}

.z-tabs__item--disabled {
	opacity: 0.5;
	pointer-events: none;
}

.z-tabs__item:active:not(.z-tabs__item--disabled) {
	opacity: 0.8;
}

/* 图标 */
.z-tabs__icon {
	margin-right: 8rpx;
}

/* 文本 */
.z-tabs__text {
	line-height: 1.2;
	transition: all 0.3s ease;
}

/* 徽标 */
.z-tabs__badge {
	position: absolute;
	top: 8rpx;
	right: 16rpx;
	min-width: 32rpx;
	height: 32rpx;
	padding: 0 8rpx;
	background: #ef4444;
	border-radius: 32rpx;
	display: flex;
	align-items: center;
	justify-content: center;
}

.z-tabs__badge-text {
	font-size: 20rpx;
	color: #ffffff;
	line-height: 1;
}

/* 红点 */
.z-tabs__dot {
	position: absolute;
	top: 12rpx;
	right: 20rpx;
	width: 16rpx;
	height: 16rpx;
	background: #ef4444;
	border-radius: 50%;
}

/* 指示器 */
.z-tabs__indicator {
	position: absolute;
	bottom: 0;
}

/* line 类型样式 */
.z-tabs--line .z-tabs__wrapper {
	background: transparent;
	border-bottom: 2rpx solid #e2e8f0;
}

.z-tabs--line .z-tabs__indicator {
	bottom: -2rpx;
}

/* card 类型样式 */
.z-tabs--card .z-tabs__wrapper {
	padding: 8rpx;
}

.z-tabs--card .z-tabs__item--active {
	background: #ffffff;
	border-radius: 8rpx;
	box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.06);
}

.z-tabs--card .z-tabs__indicator {
	display: none;
}

/* pill 类型样式 */
.z-tabs--pill .z-tabs__item {
	margin: 0 4rpx;
}
</style>
