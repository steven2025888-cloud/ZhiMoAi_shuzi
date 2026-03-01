<template>
	<view class="zct-wrapper">
		<view class="zct-root">
			<!-- Trigger -->
			<view :id="triggerId" class="zct-trigger" :class="[triggerCls, disabled ? 'is-disabled' : '', triggerClass]"
				:style="[triggerStyle]" @touchstart="onTouchStart" @touchend="onTouchEnd" @tap="onTap" @click="onTap"
				@contextmenu.prevent>
				<template v-if="as === 'text'">
					<text class="zct-text" :style="[textStyle]">
						<slot>{{ text }}</slot>
					</text>
				</template>
				<template v-else>
					<view class="zct-view" :style="[textStyle]">
						<slot>{{ text }}</slot>
					</view>
				</template>
			</view>

			<!-- Popover - 使用 z-popover 的定位方式，无遮罩层 -->
			<view v-if="open" :id="menuId" class="zct-menu"
				:class="[
					menuCls,
					`zct-menu--${resolvedPlacement}`,
					{ 'zct-menu--show': isShow },
					themeClass,
					blur ? 'is-blur' : '',
					shadow ? 'is-shadow' : '',
					menuClass
				]"
				:style="[{ zIndex: 9999 }, menuStyle]" @tap.stop @touchmove.stop.prevent @contextmenu.prevent>

				<view class="zct-menu__inner" :style="[innerStyle]">
					<view v-for="(a, i) in normalizedActions" :key="i" class="zct-item"
						:class="[a.type === 'danger' ? 'is-danger' : '', a.className || '']"
						:style="[itemStyle, a.style || {}, a.type === 'danger' ? dangerItemStyle : {}]"
						@tap.stop="onActionTap(i)">
						<text class="zct-item__txt" :style="[itemTextStyle]">{{ a.text }}</text>
					</view>
				</view>
			</view>
		</view>

		<!-- 全局点击监听层 - 放在 root 外面确保覆盖全屏 -->
		<view v-if="showBackdrop" class="zct-backdrop zct-backdrop--active" :style="{ zIndex: 9998 }"
			@tap="handleBackdropTap"
			@click="handleBackdropTap"
			@touchstart="handleBackdropTap"
			@touchmove.stop.prevent />
	</view>
</template>

<script setup lang="ts">
	import { computed, nextTick, ref, watch, getCurrentInstance } from 'vue'

	type Trigger = 'tap' | 'longpress' | 'both'
	type Placement = 'top' | 'bottom' | 'left' | 'right' | 'auto'
	type Theme = 'light' | 'dark' | 'auto'
	export type CopyAction = {
		text : string
		value ?: string
		type ?: 'default' | 'danger'
		closeOnTap ?: boolean
		className ?: string
		style ?: Record<string, any>
	}

	const props = withDefaults(defineProps<{
		/** 展示文本（默认插槽也可覆盖） */
		text : string
		/** 实际复制内容（默认= text） */
		value ?: string

		/** 触发方式：tap/longpress/both */
		trigger ?: Trigger
		/** 是否弹出菜单；false 时触发即复制 */
		showMenu ?: boolean

		/** 菜单方向：auto 会自动选择更合适的方向 */
		placement ?: Placement
		/** 菜单与触点/锚点的间距(px) */
		offset ?: number

		/** 是否显示默认“复制”动作 */
		showCopy ?: boolean
		/** 默认复制按钮文案 */
		copyText ?: string
		/** 额外动作 */
		actions ?: CopyAction[]

		/** 复制成功 toast */
		toast ?: boolean
		toastText ?: string

		/** 禁用 */
		disabled ?: boolean

		/** 渲染方式：text / view */
		as ?: 'text' | 'view'

		/** 主题：light/dark/auto */
		theme ?: Theme

		/** zIndex（overlay 与 menu） */
		zIndex ?: number

		/** Apple 风格参数 */
		radius ?: number        // rpx
		blur ?: boolean
		shadow ?: boolean
		showArrow ?: boolean

		/** ——可自定义样式/类名—— */
		triggerClass ?: string
		menuClass ?: string
		triggerStyle ?: Record<string, any> | string
		textStyle ?: Record<string, any> | string
		overlayStyle ?: Record<string, any> | string
		menuStyle ?: Record<string, any> | string
		itemStyle ?: Record<string, any> | string
		dangerItemStyle ?: Record<string, any> | string
		itemTextStyle ?: Record<string, any> | string
	}>(), {
		value: '',
		trigger: 'longpress',
		showMenu: true,
		placement: 'bottom',
		offset: 10,

		showCopy: true,
		copyText: '复制',
		actions: () => [],

		toast: true,
		toastText: '已复制',

		disabled: false,
		as: 'text',

		theme: 'auto',
		zIndex: 999,

		radius: 26,
		blur: true,
		shadow: true,
		showArrow: true,

		triggerClass: '',
		menuClass: '',
		triggerStyle: () => ({}),
		textStyle: () => ({}),
		overlayStyle: () => ({}),
		menuStyle: () => ({}),
		itemStyle: () => ({}),
		dangerItemStyle: () => ({}),
		itemTextStyle: () => ({})
	})

	const emit = defineEmits<{
		(e : 'copy', value : string) : void
		(e : 'action', payload : { index : number; action : CopyAction; text : string; value : string }) : void
		(e : 'open') : void
		(e : 'close') : void
	}>()

	// H5 平台检测：H5 默认使用 tap，其他平台使用 longpress
	const effectiveTrigger = computed(() => {
		// 如果用户明确指定了 trigger，使用用户指定的
		if (props.trigger !== 'longpress') return props.trigger

		// 否则在 H5 上默认使用 tap
		// #ifdef H5
		return 'tap'
		// #endif

		// #ifndef H5
		return 'longpress'
		// #endif
	})


	const open = ref(false)
	const isShow = ref(false)
	const isProcessing = ref(false)  // 添加处理标志，防止重复点击
	const showBackdrop = ref(false)  // 单独控制 backdrop 显示

	const pressTimer = ref<any>(null)
	const didLongpress = ref(false)

	function clearPressTimer() {
		if (pressTimer.value) {
			clearTimeout(pressTimer.value)
			pressTimer.value = null
		}
	}

	const resolvedPlacement = ref<Exclude<Placement, 'auto'>>('bottom')

	const uid = Math.random().toString(36).slice(2, 9)
	const triggerId = `zct_tr_${uid}`
	const menuId = `zct_me_${uid}`
	const triggerCls = `zct_trc_${uid}`
	const menuCls = `zct_mec_${uid}`

	const normalizedActions = computed(() => {
		const list : CopyAction[] = []
		if (props.showCopy) list.push({ text: props.copyText, type: 'default', closeOnTap: true })
		// 额外动作
		props.actions.forEach(a => list.push({
			text: a.text,
			value: a.value,
			type: a.type || 'default',
			closeOnTap: a.closeOnTap !== false,
			className: a.className,
			style: a.style
		}))
		return list
	})

	const themeClass = computed(() => {
		if (props.theme === 'light') return 'is-light'
		if (props.theme === 'dark') return 'is-dark'
		// auto：尽量跟随系统/页面，若取不到就 light
		// @ts-ignore
		const sys = uni.getSystemInfoSync?.() || {}
		// @ts-ignore
		const isDark = sys?.theme === 'dark'
		return isDark ? 'is-dark' : 'is-light'
	})

	const innerStyle = computed(() => ({
		borderRadius: `${props.radius}rpx`,
		overflow: 'hidden'
	}))

	function onTouchStart(e : any) {
		if (props.disabled) return

		console.log('onTouchStart, effectiveTrigger:', effectiveTrigger.value)

		didLongpress.value = false
		clearPressTimer()

		// 用定时器模拟 longpress，H5/APP 更稳定
		if (effectiveTrigger.value === 'longpress' || effectiveTrigger.value === 'both') {
			pressTimer.value = setTimeout(() => {
				console.log('longpress timer fired')
				didLongpress.value = true
				void openPop()
			}, 480)
		}
	}

	function onTouchEnd(_e : any) {
		console.log('onTouchEnd, didLongpress:', didLongpress.value)
		clearPressTimer()
		// 重置 didLongpress，但延迟一点以确保 tap 事件能正确检查
		setTimeout(() => {
			if (didLongpress.value) {
				console.log('resetting didLongpress after longpress')
				didLongpress.value = false
			}
		}, 50)
	}

	function onTap(e : any) {
		if (props.disabled) {
			console.log('onTap: disabled')
			return
		}
		if (isProcessing.value) {
			console.log('onTap: already processing, ignoring')
			return
		}

		console.log('onTap triggered, open:', open.value, 'didLongpress:', didLongpress.value, 'effectiveTrigger:', effectiveTrigger.value)

		// 如果菜单已经打开，关闭它
		if (open.value) {
			console.log('onTap: menu already open, closing')
			close()
			return
		}

		// 如果刚触发过长按，放过 tap（避免重复）
		if (didLongpress.value) {
			console.log('onTap: ignoring because longpress just fired')
			return
		}

		if (effectiveTrigger.value === 'tap' || effectiveTrigger.value === 'both') {
			console.log('onTap: opening menu')
			isProcessing.value = true
			void openPop().finally(() => {
				setTimeout(() => {
					isProcessing.value = false
					console.log('onTap: processing complete')
				}, 50)  // 减少到 50ms
			})
		} else {
			console.log('onTap: effectiveTrigger does not allow tap')
		}
	}

	function handleBackdropTap() {
		console.log('backdrop tapped, closing menu')
		close()
	}

	function close() {
		console.log('close called, open:', open.value)
		if (!open.value) return

		// 立即隐藏 backdrop，不阻挡其他元素的点击
		showBackdrop.value = false

		// 菜单动画延迟关闭
		isShow.value = false
		setTimeout(() => {
			open.value = false
			emit('close')
			console.log('menu closed')
		}, 300)
	}

	async function openPop() {
		console.log('openPop called, showMenu:', props.showMenu, 'placement:', props.placement)

		if (!props.showMenu) {
			await doCopy((props.value && props.value.length > 0) ? props.value : props.text)
			return
		}

		// 设置 placement - 如果是 auto 则默认 bottom
		if (props.placement === 'auto') {
			resolvedPlacement.value = 'bottom'
		} else {
			resolvedPlacement.value = props.placement as Exclude<Placement, 'auto'>
		}

		console.log('resolvedPlacement:', resolvedPlacement.value)

		open.value = true
		showBackdrop.value = true  // 显示 backdrop
		emit('open')
		await nextTick()
		setTimeout(() => {
			isShow.value = true
			console.log('menu shown')
		}, 50)
	}

	async function onActionTap(i : number) {
		const a = normalizedActions.value[i]
		if (!a) return

		// copy action: first item default
		if (props.showCopy && i === 0) {
			const v = (props.value && props.value.length > 0) ? props.value : props.text
			await doCopy(v)
			return
		}

		const v = (a.value != null && a.value !== '') ? a.value : ((props.value && props.value.length > 0) ? props.value : props.text)
		emit('action', { index: i, action: a, text: props.text, value: v })
		if (a.closeOnTap !== false) close()
	}

	async function doCopy(v : string) {
		const ok = await copyToClipboard(v)
		if (ok) {
			emit('copy', v)
			if (props.toast) uni.showToast({ title: props.toastText, icon: 'none', duration: 1200 })
		} else {
			uni.showToast({ title: '复制失败', icon: 'none', duration: 1500 })
		}
		close()
	}

	/** 我们自己封装：跨端复制（不依赖第三方 js） */
	async function copyToClipboard(text : string) : Promise<boolean> {
		try {
			await new Promise<void>((resolve, reject) => {
				uni.setClipboardData({
					data: text,
					success: () => resolve(),
					fail: () => reject(new Error('setClipboardData fail'))
				})
			})
			return true
		} catch (e) {
			// H5 fallback
			// @ts-ignore
			const nav : any = typeof navigator !== 'undefined' ? navigator : null
			try {
				if (nav?.clipboard?.writeText) {
					await nav.clipboard.writeText(text)
					return true
				}
			} catch (e2) { }

			try {
				if (typeof document !== 'undefined') {
					const ta = document.createElement('textarea')
					ta.value = text
					ta.style.position = 'fixed'
					ta.style.left = '-9999px'
					ta.style.top = '0'
					document.body.appendChild(ta)
					ta.focus()
					ta.select()
					const ok = document.execCommand('copy')
					document.body.removeChild(ta)
					return !!ok
				}
			} catch (e3) { }
			return false
		}
	}

	// 监听 open 状态，添加全局点击监听
	watch(open, (val) => {
		console.log('open changed:', val)
		if (val) {
			// 菜单打开时，延迟一帧添加全局点击监听
			nextTick(() => {
				console.log('menu opened, backdrop should be visible')
			})
		}
	})
</script>

<style scoped>
	/* ---- H5 长按浏览器菜单/选择文本抑制 ---- */
	.zct-trigger,
	.zct-menu,
	.zct-menu__inner,
	.zct-item,
	.zct-text,
	.zct-view {
		-webkit-touch-callout: none;
		-webkit-user-select: none;
		user-select: none;
	}

	/* wrapper */
	.zct-wrapper {
		display: inline-block;
		/* 不要使用 transform，否则会影响 fixed 定位 */
	}

	/* root */
	.zct-root {
		position: relative;
		display: inline-block;
		/* 不要使用 transform，否则会影响 fixed 定位 */
	}

	.zct-trigger {
		display: inline-flex;
		align-items: center;
		transition: all 0.2s ease;
	}

	.zct-trigger:active {
		opacity: 0.7;
		transform: scale(0.98);
	}

	/* backdrop - 透明的全局点击层 */
	.zct-backdrop {
		position: fixed !important;
		left: 0 !important;
		top: 0 !important;
		right: 0 !important;
		bottom: 0 !important;
		width: 100vw !important;
		height: 100vh !important;
		background: transparent !important;  /* 改回透明 */
		pointer-events: auto !important;
		cursor: pointer !important;
		touch-action: auto !important;
		/* 确保不受父元素影响 */
		margin: 0 !important;
		padding: 0 !important;
		transform: none !important;
		/* 立即显示，无过渡 */
		transition: none !important;
		opacity: 1 !important;
		visibility: visible !important;
	}

	/* menu - 使用 z-popover 的定位方式 */
	.zct-menu {
		position: absolute;
		display: flex;
		min-width: 220rpx;
		max-width: 620rpx;
		opacity: 0;
		visibility: hidden;
		transform: scale(0.9);
		transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
		border-radius: 32rpx;
	}

	.zct-menu--show {
		opacity: 1;
		visibility: visible;
		transform: scale(1);
	}

	/* 位置定位 - 参考 z-popover */
	.zct-menu--top {
		flex-direction: column;
		left: 50%;
		bottom: 100%;
		transform: translateX(-50%) scale(0.9);
		transform-origin: center bottom;
		margin-bottom: 8rpx;
	}

	.zct-menu--top.zct-menu--show {
		transform: translateX(-50%) scale(1);
	}

	.zct-menu--bottom {
		flex-direction: column;
		left: 50%;
		top: 100%;
		transform: translateX(-50%) scale(0.9);
		transform-origin: center top;
		margin-top: 8rpx;
	}

	.zct-menu--bottom.zct-menu--show {
		transform: translateX(-50%) scale(1);
	}

	.zct-menu--left {
		flex-direction: row;
		right: 100%;
		top: 50%;
		transform: translateY(-50%) scale(0.9);
		transform-origin: right center;
		margin-right: 8rpx;
	}

	.zct-menu--left.zct-menu--show {
		transform: translateY(-50%) scale(1);
	}

	.zct-menu--right {
		flex-direction: row;
		left: 100%;
		top: 50%;
		transform: translateY(-50%) scale(0.9);
		transform-origin: left center;
		margin-left: 8rpx;
	}

	.zct-menu--right.zct-menu--show {
		transform: translateY(-50%) scale(1);
	}

	.zct-menu__inner {
		border: 1px solid rgba(0, 0, 0, .08);
		overflow: hidden;
		position: relative;
		width: 100%;
		height: 100%;
	}

	.zct-menu.is-light .zct-menu__inner {
		background: rgba(255, 255, 255, .92);
	}

	.zct-menu.is-dark .zct-menu__inner {
		background: rgba(30, 30, 30, .85);
		border-color: rgba(255, 255, 255, .12);
	}

	/* blur */
	.zct-menu.is-blur .zct-menu__inner {
		backdrop-filter: blur(24px) saturate(180%);
		-webkit-backdrop-filter: blur(24px) saturate(180%);
	}

	/* shadow */
	.zct-menu.is-shadow.is-light {
		box-shadow: 0 20rpx 70rpx rgba(0, 0, 0, .20), 0 4rpx 16rpx rgba(0, 0, 0, .10);
	}

	.zct-menu.is-shadow.is-dark {
		box-shadow: 0 20rpx 70rpx rgba(0, 0, 0, .50), 0 4rpx 16rpx rgba(0, 0, 0, .30);
	}

	/* item */
	.zct-item {
		padding: 24rpx 32rpx;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s ease;
		position: relative;
	}

	.zct-item::before {
		content: '';
		position: absolute;
		left: 0;
		right: 0;
		top: 0;
		bottom: 0;
		background: transparent;
		transition: all 0.2s ease;
		border-radius: 0;
	}

	.zct-item:first-child::before {
		border-top-left-radius: 32rpx;
		border-top-right-radius: 32rpx;
	}

	.zct-item:last-child::before {
		border-bottom-left-radius: 32rpx;
		border-bottom-right-radius: 32rpx;
	}

	.zct-item+.zct-item {
		border-top: 1px solid rgba(0, 0, 0, .06);
	}

	.zct-menu.is-dark .zct-item+.zct-item {
		border-top-color: rgba(255, 255, 255, .08);
	}

	.zct-item__txt {
		font-size: 30rpx;
		line-height: 1.3;
		font-weight: 600;
		position: relative;
		z-index: 1;
		letter-spacing: 0.3rpx;
	}

	.zct-menu.is-light .zct-item__txt {
		color: rgba(0, 0, 0, .90);
	}

	.zct-menu.is-dark .zct-item__txt {
		color: rgba(255, 255, 255, .90);
	}

	.zct-item:active::before {
		background: rgba(0, 0, 0, .08);
	}

	.zct-menu.is-dark .zct-item:active::before {
		background: rgba(255, 255, 255, .10);
	}

	.zct-item.is-danger .zct-item__txt {
		color: #ff3b30;
		font-weight: 700;
	}

	/* disabled */
	.is-disabled {
		opacity: .50;
	}
</style>