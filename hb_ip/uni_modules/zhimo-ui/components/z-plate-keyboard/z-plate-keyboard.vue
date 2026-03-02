<template>
	<view class="z-pk" :class="[
		'z-pk--' + theme,
		{ 'z-pk--show': show, 'z-pk--safe': iphoneX && safeArea }
	]" :style="{ zIndex }" ref="pkRef">
		<slot></slot>

		<!-- 工具栏 -->
		<view v-if="showToolbar" class="z-pk__toolbar" :class="['z-pk__toolbar--' + theme]">
			<view class="z-pk__toolbar-left">
				<text class="z-pk__toolbar-tip" :class="['z-pk__toolbar-tip--' + theme]">
					{{ keyboardType === 1 ? '省份简称' : '字母数字' }}
				</text>
			</view>
			<text class="z-pk__done" :style="{ color: doneColor, fontSize: doneFontSize + 'rpx', fontWeight: String(doneFontWeight) }"
				@click.stop="onDone">{{ doneText }}</text>
		</view>

		<!-- 键盘区域 -->
		<view class="z-pk__keys">
			<view v-for="(row, ri) in currentKeys" :key="ri" class="z-pk__row">
				<!-- 切换按钮 (最后一行首位) -->
				<view v-if="ri === 3" class="z-pk__key z-pk__key--func" :class="['z-pk__key--' + theme]"
					@click.stop="toggleKeyboard">
					<text class="z-pk__key-text z-pk__key-text--func" :class="['z-pk__key-text--' + theme]">
						{{ keyboardType === 1 ? 'ABC' : '省份' }}
					</text>
				</view>

				<!-- 普通按键 -->
				<view v-for="(key, ki) in row.keys" :key="ki" class="z-pk__key"
					:class="[
						'z-pk__key--' + theme,
						{ 'z-pk__key--hidden': !getKeyText(key) }
					]" @click.stop="onKeyClick(key)">
					<text class="z-pk__key-text" :class="['z-pk__key-text--' + theme]"
						:style="{ fontSize: (keyboardType === 1 ? 32 : 34) + 'rpx' }">
						{{ getKeyText(key) }}
					</text>
				</view>

				<!-- 删除按钮 (最后一行末尾) -->
				<view v-if="ri === 3" class="z-pk__key z-pk__key--func" :class="['z-pk__key--' + theme]"
					@click.stop="onBackspace">
					<z-icon name="mdi:backspace-outline" :size="44" :color="theme === 'light' ? '#1C1C1E' : '#E5E5EA'" />
				</view>
			</view>
		</view>
	</view>
</template>

<script>
export default { name: 'z-plate-keyboard' }
</script>

<script setup>
import { ref, computed, onMounted } from 'vue'

// ---- 键盘数据 (内嵌,无需外部js) ----
const PROVINCE_KEYS = [
	{
		keys: [
			{ cn: '京', en: '1' }, { cn: '津', en: '2' }, { cn: '沪', en: '3' },
			{ cn: '渝', en: '4' }, { cn: '冀', en: '5' }, { cn: '豫', en: '6' },
			{ cn: '云', en: '7' }, { cn: '辽', en: '8' }, { cn: '黑', en: '9' },
			{ cn: '湘', en: '0' }
		]
	},
	{
		keys: [
			{ cn: '皖', en: 'Q' }, { cn: '鲁', en: 'W' }, { cn: '新', en: 'E' },
			{ cn: '苏', en: 'R' }, { cn: '浙', en: 'T' }, { cn: '赣', en: 'Y' },
			{ cn: '鄂', en: 'U' }, { cn: '桂', en: 'I' }, { cn: '甘', en: 'O' },
			{ cn: '晋', en: 'P' }
		]
	},
	{
		keys: [
			{ cn: '蒙', en: 'A' }, { cn: '陕', en: 'S' }, { cn: '吉', en: 'D' },
			{ cn: '闽', en: 'F' }, { cn: '贵', en: 'G' }, { cn: '粤', en: 'H' },
			{ cn: '青', en: 'J' }, { cn: '藏', en: 'K' }, { cn: '川', en: 'L' },
			{ cn: '宁', en: '' }
		]
	},
	{
		keys: [
			{ cn: '琼', en: 'Z' }, { cn: '使', en: 'X' }, { cn: '领', en: 'C' },
			{ cn: '学', en: 'V' }, { cn: '警', en: 'B' }, { cn: '港', en: 'N' },
			{ cn: '澳', en: 'M' }
		]
	}
]

// 字母数字键盘 (第2位只能字母，第3-7/8位字母+数字，排除I和O)
const LETTER_NUMBER_KEYS = [
	{
		keys: [
			{ text: '1' }, { text: '2' }, { text: '3' }, { text: '4' }, { text: '5' },
			{ text: '6' }, { text: '7' }, { text: '8' }, { text: '9' }, { text: '0' }
		]
	},
	{
		keys: [
			{ text: 'Q' }, { text: 'W' }, { text: 'E' }, { text: 'R' }, { text: 'T' },
			{ text: 'Y' }, { text: 'U' }, { text: 'P' }
		]
	},
	{
		keys: [
			{ text: 'A' }, { text: 'S' }, { text: 'D' }, { text: 'F' }, { text: 'G' },
			{ text: 'H' }, { text: 'J' }, { text: 'K' }, { text: 'L' }
		]
	},
	{
		keys: [
			{ text: 'Z' }, { text: 'X' }, { text: 'C' }, { text: 'V' },
			{ text: 'B' }, { text: 'N' }, { text: 'M' }
		]
	}
]

const props = defineProps({
	// 显示/隐藏
	show: { type: Boolean, default: false },
	// 显示工具栏
	showToolbar: { type: Boolean, default: true },
	// 完成按钮文字
	doneText: { type: String, default: '完成' },
	// 完成按钮颜色
	doneColor: { type: String, default: '#007AFF' },
	// 完成按钮字号 rpx
	doneFontSize: { type: [Number, String], default: 30 },
	// 完成按钮字重
	doneFontWeight: { type: [Number, String], default: 600 },
	// 主题: light / dark
	theme: { type: String, default: 'light' },
	// z-index
	zIndex: { type: [Number, String], default: 1001 },
	// 底部安全区
	safeArea: { type: Boolean, default: true },
	// 当前输入值
	value: { type: String, default: '' },
	// 车牌长度 (7或8)
	length: { type: Number, default: 7 }
})

const emit = defineEmits(['input', 'delete', 'done', 'update:show'])

// 1=省份 2=字母数字
const keyboardType = ref(1)
const iphoneX = ref(false)

// 根据输入位置自动切换键盘
const currentKeys = computed(() => {
	const inputLength = props.value.length

	// 第1位：省份键盘
	if (inputLength === 0) {
		keyboardType.value = 1
		return PROVINCE_KEYS
	}

	// 第2位及以后：字母数字键盘
	keyboardType.value = 2

	// 第2位只能是字母
	if (inputLength === 1) {
		return LETTER_NUMBER_KEYS.map((row, index) => {
			if (index === 0) {
				// 第一行数字，全部隐藏
				return { keys: row.keys.map(k => ({ ...k, text: '' })) }
			}
			return row
		})
	}

	// 第3-7/8位：字母+数字，但排除I和O
	return LETTER_NUMBER_KEYS.map(row => {
		return {
			keys: row.keys.filter(k => k.text !== 'I' && k.text !== 'O')
		}
	})
})

onMounted(() => {
	iphoneX.value = checkSafeArea()
})

function getKeyText(key) {
	// 省份键盘
	if (keyboardType.value === 1) {
		return key.cn
	}
	// 字母数字键盘
	return key.text || ''
}

function toggleKeyboard() {
	// 手动切换已禁用，键盘会根据输入位置自动切换
	// 保留此函数以防外部调用
}

function onKeyClick(key) {
	const text = getKeyText(key)
	if (!text || !props.show) return
	emit('input', { value: text })
}

function onBackspace() {
	if (!props.show) return
	emit('delete', {})
}

function onDone() {
	if (!props.show) return
	emit('update:show', false)
	emit('done', {})
}

function switchKeyboard(type = 'en') {
	keyboardType.value = type === 'en' ? 2 : 1
}

function checkSafeArea() {
	if (!props.safeArea) return false
	try {
		const res = uni.getSystemInfoSync()
		return res.safeAreaInsets && res.safeAreaInsets.bottom > 0
	} catch (e) {
		return false
	}
}

defineExpose({ switchKeyboard })
</script>

<style scoped>
.z-pk {
	/* #ifndef APP-NVUE */
	width: 100%;
	visibility: hidden;
	transform: translate3d(0, 100%, 0);
	transition: transform 0.3s cubic-bezier(0.32, 0.72, 0, 1), visibility 0.3s;
	overflow: hidden;
	box-sizing: border-box;
	/* #endif */
	position: fixed;
	left: 0;
	right: 0;
	bottom: 0;
	/* #ifndef APP-NVUE || MP-TOUTIAO */
	padding-bottom: constant(safe-area-inset-bottom);
	padding-bottom: env(safe-area-inset-bottom);
	/* #endif */
}

.z-pk--show {
	/* #ifndef APP-NVUE */
	visibility: visible;
	transform: translate3d(0, 0, 0);
	/* #endif */
}

/* #ifdef APP-NVUE || MP-TOUTIAO */
.z-pk--safe {
	padding-bottom: 34px;
}
/* #endif */

.z-pk--light {
	background: #D1D3D9;
}

.z-pk--dark {
	background: #1B1B1B;
}

/* ---- 工具栏 ---- */
.z-pk__toolbar {
	/* #ifndef APP-NVUE */
	display: flex;
	box-sizing: border-box;
	/* #endif */
	flex-direction: row;
	align-items: center;
	justify-content: space-between;
	padding: 20rpx 24rpx;
}

.z-pk__toolbar--light {
	background: #ECEDF0;
}

.z-pk__toolbar--dark {
	background: #2C2C2E;
}

.z-pk__toolbar-left {
	flex: 1;
	/* #ifndef APP-NVUE */
	display: flex;
	/* #endif */
	flex-direction: row;
	align-items: center;
}

.z-pk__toolbar-tip {
	font-size: 24rpx;
	font-weight: 400;
}

.z-pk__toolbar-tip--light {
	color: #8E8E93;
}

.z-pk__toolbar-tip--dark {
	color: #636366;
}

.z-pk__done {
	padding: 8rpx 24rpx;
	font-size: 30rpx;
	font-weight: 600;
	/* #ifdef H5 */
	cursor: pointer;
	/* #endif */
}

.z-pk__done:active {
	opacity: 0.5;
}

/* ---- 键盘区 ---- */
.z-pk__keys {
	/* #ifndef APP-NVUE */
	width: 100%;
	box-sizing: border-box;
	/* #endif */
	padding: 16rpx 8rpx 8rpx;
}

.z-pk__row {
	/* #ifndef APP-NVUE */
	display: flex;
	width: 100%;
	/* #endif */
	flex-direction: row;
	align-items: center;
	justify-content: center;
	margin-bottom: 12rpx;
}

/* ---- 按键 ---- */
.z-pk__key {
	/* #ifndef APP-NVUE */
	display: flex;
	flex-shrink: 0;
	box-sizing: border-box;
	transition: background 0.1s ease;
	/* #endif */
	width: 66rpx;
	height: 84rpx;
	margin: 0 4rpx;
	border-radius: 10rpx;
	align-items: center;
	justify-content: center;
	/* #ifdef H5 */
	cursor: pointer;
	user-select: none;
	/* #endif */
}

.z-pk__key--func {
	width: 100rpx;
}

.z-pk__key--light {
	background: #FFFFFF;
	/* #ifndef APP-NVUE */
	box-shadow: 0 2rpx 0 #A8AAB0;
	/* #endif */
}

.z-pk__key--dark {
	background: #555555;
	/* #ifndef APP-NVUE */
	box-shadow: 0 2rpx 0 #000000;
	/* #endif */
}

.z-pk__key--light:active {
	background: #C8C9CC;
}

.z-pk__key--dark:active {
	background: #777777;
}

.z-pk__key--hidden {
	width: 0;
	margin: 0;
	padding: 0;
	opacity: 0;
	overflow: hidden;
}

.z-pk__key-text {
	font-weight: 500;
	text-align: center;
}

.z-pk__key-text--light {
	color: #1C1C1E;
}

.z-pk__key-text--dark {
	color: #E5E5EA;
}

.z-pk__key-text--func {
	font-size: 26rpx !important;
	font-weight: 500;
}
</style>
