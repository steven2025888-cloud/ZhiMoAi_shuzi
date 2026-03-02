<template>
	<!-- ====== APP-NVUE ====== -->
	<!-- #ifdef APP-NVUE -->
	<view class="z-drag-sort" ref="sortWrap" :style="wrapStyle">
		<view v-for="(node, idx) in nodes" :key="node._id" class="z-drag-sort__cell" :ref="'cell_' + idx"
			:style="{ width: cellW + 'px', height: cellH + 'px' }" :data-idx="idx" fireEventSync="true"
			@longpress="nvueLongPress" @touchstart="nvueTouchStart" @touchmove="nvueTouchMove"
			@touchend="nvueTouchEnd" @tap="onCellTap(idx)">
			<template v-if="custom">
				<slot :item="node.data" :width="cellW" :height="cellH" :index="idx" />
			</template>
			<template v-else>
				<z-drag-sort-item :width="cellW" :height="cellH" :image="pickField(node.data, imageKey)"
					:label="pickField(node.data, labelKey)" :mode="viewMode" :show-delete="showDelete"
					:show-handle="showHandle" :index="idx" :padding="itemPadding" :background="itemBackground"
					:radius="itemRadius" :font-size="itemFontSize" :text-color="itemTextColor"
					@delete="onItemDelete" />
			</template>
		</view>
	</view>
	<!-- #endif -->

	<!-- ====== 非NVUE (H5 / App-Vue / 小程序) ====== -->
	<!-- #ifndef APP-NVUE -->
	<view class="z-drag-sort" :id="uid" :style="wrapStyle" @touchmove="onContainerTouchMove">
		<view v-for="(node, idx) in nodes" :key="node._id" class="z-drag-sort__cell"
			:class="{ 'z-drag-sort__cell--active': activeIdx === idx }" :style="getCellStyle(idx, node)"
			:data-idx="idx" @longpress="onLongPress" @touchstart="onTouchStart" @touchend="onTouchEnd"
			@mousedown="onMouseDown" @tap="onCellTap(idx)">
			<template v-if="custom">
				<slot :item="node.data" :width="cellW" :height="cellH" :index="idx" />
			</template>
			<template v-else>
				<z-drag-sort-item :width="cellW" :height="cellH" :image="pickField(node.data, imageKey)"
					:label="pickField(node.data, labelKey)" :mode="viewMode" :show-delete="showDelete"
					:show-handle="showHandle" :index="idx" :padding="itemPadding" :background="itemBackground"
					:radius="itemRadius" :font-size="itemFontSize" :text-color="itemTextColor"
					@delete="onItemDelete" />
			</template>
		</view>
	</view>
	<!-- #endif -->
</template>

<script>
// #ifdef APP-NVUE
const domModule = uni.requireNativePlugin('dom')
const animModule = uni.requireNativePlugin('animation')
// #endif

import { defineComponent, ref, computed, watch, nextTick, onMounted, getCurrentInstance } from 'vue'

let _idCounter = 0
function makeId() {
	return 'zds_' + (++_idCounter) + '_' + Date.now()
}

export default defineComponent({
	name: 'z-drag-sort',
	emits: ['change', 'sort-end', 'item-click', 'delete'],
	props: {
		list: { type: Array, default: () => [] },
		columns: { type: [Number, String], default: 1 },
		itemHeight: { type: [Number, String], default: 0 },
		square: { type: Boolean, default: false },
		width: { type: [Number, String], default: 0 },
		draggable: { type: Boolean, default: true },
		custom: { type: Boolean, default: false },
		mode: { type: String, default: '' },
		imageKey: { type: String, default: 'image' },
		labelKey: { type: String, default: 'label' },
		scrollTop: { type: Number, default: 0 },
		showDelete: { type: Boolean, default: false },
		showHandle: { type: Boolean, default: true },
		itemPadding: { type: Number, default: 6 },
		itemBackground: { type: String, default: '#ffffff' },
		itemRadius: { type: [Number, String], default: 8 },
		itemFontSize: { type: [Number, String], default: 30 },
		itemTextColor: { type: String, default: '#333333' }
	},
	setup(props, { emit }) {
		const instance = getCurrentInstance()
		const uid = 'zds_' + Math.ceil(Math.random() * 10e5).toString(36)

		// ==================== 通用状态 ====================
		const nodes = ref([])
		const cellW = ref(0)
		const cellH = ref(0)
		const rows = ref(0)
		const containerW = ref(0)
		const screenH = ref(0)
		let skipListWatch = false

		const wrapStyle = computed(() => {
			const s = { height: (rows.value * cellH.value) + 'px' }
			// #ifdef APP-NVUE
			if (containerW.value > 0) s.width = containerW.value + 'px'
			// #endif
			return s
		})
		const viewMode = computed(() => {
			if (props.mode) return props.mode
			return Number(props.columns) > 1 ? 'grid' : 'list'
		})

		function pickField(obj, key) {
			if (!obj || !key) return ''
			return obj[key] || ''
		}

		// ==================== 布局初始化 ====================
		function queryRect(cb, retry = 0) {
			// #ifndef APP-NVUE
			uni.createSelectorQuery()
				// #ifndef MP-ALIPAY
				.in(instance.proxy)
				// #endif
				.select('#' + uid)
				.boundingClientRect()
				.exec(res => {
					if (retry >= 10) return
					if (!res || !res[0]) {
						setTimeout(() => queryRect(cb, retry + 1), 50)
						return
					}
					cb({ width: res[0].width })
				})
			// #endif
			// #ifdef APP-NVUE
			domModule.getComponentRect(instance.proxy.$refs.sortWrap, res => {
				if (res && res.size) cb({ width: res.size.width })
			})
			// #endif
		}

		function rebuild() {
			const sys = uni.getSystemInfoSync()
			screenH.value = sys.windowHeight
			rows.value = Math.max(1, Math.ceil(props.list.length / Number(props.columns)))

			const propW = Number(props.width)
			if (propW > 0) {
				const fixedW = uni.upx2px(propW)
				containerW.value = fixedW
				cellW.value = fixedW / Number(props.columns)
				cellH.value = props.square ? cellW.value : uni.upx2px(props.itemHeight)
			}

			nextTick(() => {
				queryRect((rect) => {
					const realW = propW > 0 ? uni.upx2px(propW) : rect.width
					containerW.value = realW
					const cols = Number(props.columns)
					cellW.value = realW / cols
					cellH.value = props.square ? cellW.value : uni.upx2px(props.itemHeight)

					const items = JSON.parse(JSON.stringify(props.list))
					rows.value = Math.ceil(items.length / cols)
					if (items.length === 0) { nodes.value = []; return }

					nodes.value = items.map((item, i) => ({
						_id: makeId(),
						idx: i,
						order: i,
						tx: (i % cols) * cellW.value,
						ty: Math.floor(i / cols) * cellH.value,
						data: item
					}))

					// #ifdef APP-NVUE
					nextTick(() => setTimeout(() => nvueInitRefs(), 50))
					// #endif
				})
			})
		}

		// ==================== 排序核心 ====================
		function reorder(fromPos, toPos) {
			const cols = Number(props.columns)
			let targetIdx = -1
			nodes.value.forEach(n => { if (n.order === toPos) targetIdx = n.idx })
			return nodes.value.map(n => {
				let p = n.order, k = n.idx
				if (fromPos < toPos) {
					if (p > fromPos && p <= toPos) { p--; k-- }
					else if (p === fromPos) { p = toPos; k = targetIdx }
				} else if (fromPos > toPos) {
					if (p >= toPos && p < fromPos) { p++; k++ }
					else if (p === fromPos) { p = toPos; k = targetIdx }
				}
				if (n.order !== p) {
					n.tx = (p % cols) * cellW.value
					n.ty = Math.floor(p / cols) * cellH.value
					n.order = p
					n.idx = k
				}
				return n
			})
		}

		function sortedData(list) {
			const arr = []
			list.forEach(n => { arr[n.order] = n })
			return arr.map(n => n.data)
		}

		function gridOverflow(col, row, pos) {
			return col < 0 || col >= Number(props.columns) ||
				row < 0 || row >= rows.value ||
				pos < 0 || pos >= nodes.value.length
		}

		function doAutoScroll(clientY, pageY) {
			if (clientY > screenH.value - cellH.value) {
				uni.pageScrollTo({ scrollTop: pageY + cellH.value - screenH.value, duration: 0 })
			} else if (clientY < cellH.value) {
				uni.pageScrollTo({ scrollTop: pageY - cellH.value, duration: 0 })
			}
		}

		// ==================== 通用事件 ====================
		function onCellTap(idx) {
			// #ifndef APP-NVUE
			if (tapBlocked) return
			// #endif
			if (!nodes.value || !nodes.value[idx]) return
			emit('item-click', { index: nodes.value[idx].idx, item: nodes.value[idx].data })
		}
		function onItemDelete(e) { emit('delete', { index: e.index }) }

		// ==================================================================
		//  非 NVUE: Vue 响应式拖拽
		//
		//  ★ offset 锁定策略 ★
		//  长按瞬间: offsetX = clientX - node.tx, offsetY = clientY - node.ty
		//  拖动时:   newTx = clientX - offsetX,   newTy = clientY - offsetY
		//  完全不需要 containerTop / containerLeft, 与页面滚动无关
		// ==================================================================
		// #ifndef APP-NVUE
		const activeIdx = ref(-1)
		const dragTx = ref(0)
		const dragTy = ref(0)
		let dragging = false
		let savedTouch = null
		let prevOrder = -1
		let tapBlocked = false
		let pressTimer = null
		let offsetX = 0
		let offsetY = 0

		function getCellStyle(idx, node) {
			const isActive = idx === activeIdx.value
			const tx = isActive ? dragTx.value : node.tx
			const ty = isActive ? dragTy.value : node.ty
			return {
				width: cellW.value + 'px',
				height: cellH.value + 'px',
				transform: 'translate3d(' + tx + 'px,' + ty + 'px,0)' + (isActive ? ' scale(1.06)' : '')
			}
		}

		function beginDrag(idx, clientX, clientY) {
			if (dragging || !props.draggable) return
			const node = nodes.value[idx]
			if (!node) return
			activeIdx.value = idx
			dragging = true
			// 记录手指与元素当前位置的差值
			offsetX = clientX - node.tx
			offsetY = clientY - node.ty
			// 元素保持原位，不跳动
			dragTx.value = node.tx
			dragTy.value = node.ty
		}

		function moveDrag(clientX, clientY, pageY) {
			if (!dragging) return
			const cols = Number(props.columns)
			// 新位置 = 手指 - 偏移量
			const px = cols === 1 ? 0 : clientX - offsetX
			const py = clientY - offsetY
			dragTx.value = px
			dragTy.value = py

			doAutoScroll(clientY, pageY)

			const fromPos = nodes.value[activeIdx.value].order
			const gc = Math.round(px / cellW.value)
			const gr = Math.round(py / cellH.value)
			const toPos = gc + cols * gr
			if (gridOverflow(gc, gr, toPos)) return
			if (fromPos === toPos || fromPos === prevOrder) return
			prevOrder = fromPos
			const updated = reorder(fromPos, toPos)
			nodes.value = [...updated]
			emit('change', { list: sortedData(updated) })
		}

		function finishDrag() {
			if (!dragging) return
			const result = sortedData(nodes.value)
			const cur = activeIdx.value
			if (cur >= 0 && nodes.value[cur]) {
				dragTx.value = nodes.value[cur].tx
				dragTy.value = nodes.value[cur].ty
			}
			setTimeout(() => {
				activeIdx.value = -1
				dragging = false
			}, 280)
			prevOrder = -1
			tapBlocked = true
			setTimeout(() => { tapBlocked = false }, 350)
			skipListWatch = true
			emit('sort-end', { list: result })
			setTimeout(() => { skipListWatch = false }, 200)
		}

		function onTouchStart(e) {
			if (!props.draggable) return
			savedTouch = e.changedTouches[0] || e.touches[0]
		}
		function onLongPress(e) {
			if (!props.draggable || dragging) return
			const touch = (e.changedTouches && e.changedTouches[0]) || savedTouch
			if (!touch) return
			beginDrag(Number(e.currentTarget.dataset.idx), touch.clientX, touch.clientY)
		}
		function onContainerTouchMove(e) {
			if (!dragging) return
			if (e.preventDefault) e.preventDefault()
			if (e.stopPropagation) e.stopPropagation()
			const touch = e.changedTouches[0] || e.touches[0]
			if (!touch) return
			moveDrag(touch.clientX, touch.clientY, touch.pageY)
		}
		function onTouchEnd() {
			clearTimeout(pressTimer)
			finishDrag()
		}

		// H5 鼠标
		function onMouseDown(e) {
			if (typeof window === 'undefined') return
			if (!props.draggable || dragging) return
			const idx = Number(e.currentTarget.dataset.idx)
			clearTimeout(pressTimer)
			pressTimer = setTimeout(() => {
				beginDrag(idx, e.clientX, e.clientY)
				const onMove = (ev) => {
					if (!dragging) return
					ev.preventDefault()
					moveDrag(ev.clientX, ev.clientY, ev.pageY)
				}
				const onUp = () => {
					finishDrag()
					document.removeEventListener('mousemove', onMove)
					document.removeEventListener('mouseup', onUp)
				}
				document.addEventListener('mousemove', onMove)
				document.addEventListener('mouseup', onUp)
			}, 350)
			const earlyUp = () => {
				clearTimeout(pressTimer)
				document.removeEventListener('mouseup', earlyUp)
			}
			document.addEventListener('mouseup', earlyUp)
		}
		// #endif

		// ==================================================================
		//  NVUE: 原生动画 (同样使用 offset 策略)
		// ==================================================================
		// #ifdef APP-NVUE
		let nvActiveIdx = -1
		let nvDragging = false
		let nvSavedTouch = null
		let nvPrevOrder = -1
		let nvRefs = []
		let nvOffsetX = 0
		let nvOffsetY = 0
		let nvIsAndroid = false
		const sysInfo = uni.getSystemInfoSync()
		nvIsAndroid = sysInfo.platform.toLowerCase() === 'android'

		function nvueInitRefs() {
			nvRefs = []
			nodes.value.forEach((n, i) => {
				const el = instance.proxy.$refs['cell_' + i]
				if (!el) return
				const r = el.ref || el[0].ref
				nvRefs.push(r)
				nvAnimate(r, i, n.tx + 'px', n.ty + 'px')
			})
		}
		function nvAnimate(r, i, x, y) {
			animModule.transition(r, {
				styles: { transform: 'translate(' + x + ',' + y + ')' },
				duration: nvActiveIdx === i ? 0 : 250,
				timingFunction: 'linear', needLayout: false, delay: 0
			})
		}
		function nvFixTouch(t) {
			if (nvIsAndroid) { t.pageX = t.screenX; t.pageY = t.screenY }
			return t
		}
		function nvueTouchStart(e) {
			if (!props.draggable) return
			nvSavedTouch = e.changedTouches[0] || e.touches[0]
		}
		function nvueLongPress(e) {
			if (!props.draggable || nvDragging) return
			let t = (e.changedTouches && e.changedTouches[0]) || nvSavedTouch
			if (!t) return
			nvActiveIdx = Number(e.currentTarget.dataset.idx)
			const r = nvRefs[nvActiveIdx]
			if (!r) return
			t = nvFixTouch(t)
			const node = nodes.value[nvActiveIdx]
			nvOffsetX = t.pageX - node.tx
			nvOffsetY = t.pageY - node.ty
			nvAnimate(r, nvActiveIdx, node.tx + 'px', node.ty + 'px')
			nvDragging = true
		}
		function nvueTouchMove(e) {
			if (!props.draggable || !nvDragging) return
			let t = e.changedTouches[0] || e.touches[0]
			if (!t) return
			t = nvFixTouch(t)
			const cols = Number(props.columns)
			const px = cols === 1 ? 0 : t.pageX - nvOffsetX
			const py = t.pageY - nvOffsetY
			doAutoScroll(t.clientY || t.pageY, t.pageY)
			const r = nvRefs[nvActiveIdx]
			if (!r) return
			nvAnimate(r, nvActiveIdx, px + 'px', py + 'px')
			const from = nodes.value[nvActiveIdx].order
			const gc = Math.round(px / cellW.value)
			const gr = Math.round(py / cellH.value)
			const to = gc + cols * gr
			if (gridOverflow(gc, gr, to)) return
			if (from === to || from === nvPrevOrder) return
			nvPrevOrder = from
			const updated = reorder(from, to)
			nvRefs.forEach((ins, i) => {
				if (i !== nvActiveIdx) nvAnimate(ins, i, updated[i].tx + 'px', updated[i].ty + 'px')
			})
			emit('change', { list: sortedData(updated) })
		}
		function nvueTouchEnd() {
			if (!props.draggable || !nvDragging) return
			skipListWatch = true
			emit('sort-end', { list: sortedData(nodes.value) })
			setTimeout(() => { skipListWatch = false }, 200)
			const prev = nvActiveIdx
			nvActiveIdx = -1
			const r = nvRefs[prev]
			if (r) nvAnimate(r, prev, nodes.value[prev].tx + 'px', nodes.value[prev].ty + 'px')
			nvPrevOrder = -1
			nvDragging = false
		}
		// #endif

		// ==================== Watchers ====================
		watch(() => props.list, () => {
			if (skipListWatch) { skipListWatch = false; return }
			nodes.value = []
			nextTick(() => rebuild())
		}, { deep: true })
		watch(() => props.columns, () => { nodes.value = []; nextTick(() => rebuild()) })
		watch(() => props.width, () => { nodes.value = []; nextTick(() => rebuild()) })
		// #ifdef APP-NVUE
		watch(nodes, () => { nextTick(() => setTimeout(() => nvueInitRefs(), 50)) })
		// #endif

		onMounted(() => nextTick(() => rebuild()))

		// ==================== 返回 ====================
		const result = {
			uid, nodes, cellW, cellH, rows, containerW, wrapStyle, viewMode,
			pickField, onCellTap, onItemDelete
		}
		// #ifndef APP-NVUE
		Object.assign(result, {
			activeIdx, getCellStyle,
			onLongPress, onTouchStart, onContainerTouchMove, onTouchEnd, onMouseDown
		})
		// #endif
		// #ifdef APP-NVUE
		Object.assign(result, {
			nvueLongPress, nvueTouchStart, nvueTouchMove, nvueTouchEnd
		})
		// #endif
		return result
	}
})
</script>

<style scoped>
.z-drag-sort {
	/* #ifndef APP-NVUE */
	width: 100%;
	box-sizing: border-box;
	overflow: hidden;
	/* #endif */
	position: relative;
}
.z-drag-sort__cell {
	position: absolute;
	left: 0;
	top: 0;
	/* #ifndef APP-NVUE */
	display: flex;
	box-sizing: border-box;
	overflow: hidden;
	transition: transform 0.28s ease, box-shadow 0.28s ease;
	-webkit-transition: transform 0.28s ease, box-shadow 0.28s ease;
	/* #endif */
	flex-direction: column;
	align-items: center;
	justify-content: center;
	z-index: 1;
	/* #ifdef H5 */
	cursor: grab;
	user-select: none;
	-webkit-user-select: none;
	/* #endif */
}
.z-drag-sort__cell--active {
	z-index: 100 !important;
	/* #ifndef APP-NVUE */
	transition: none !important;
	-webkit-transition: none !important;
	box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
	opacity: 0.92;
	/* #endif */
	/* #ifdef H5 */
	cursor: grabbing;
	/* #endif */
}
</style>
