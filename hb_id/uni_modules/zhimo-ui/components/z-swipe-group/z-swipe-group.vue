<template>
	<view class="z-swipe-group">
		<slot></slot>
	</view>
</template>

<script setup>
/**
 * z-swipe-group 滑动菜单组
 * @description 滑动菜单的容器组件，用于管理多个滑动菜单的联动关闭
 * @example <z-swipe-group><z-swipe-action>...</z-swipe-action></z-swipe-group>
 */
import { ref, provide } from 'vue'

// 子组件列表
const children = ref([])

// 当前打开的子组件
const openItem = ref(null)

// 注册子组件
const addChild = (child) => {
	children.value.push(child)
}

// 移除子组件
const removeChild = (child) => {
	const index = children.value.indexOf(child)
	if (index > -1) {
		children.value.splice(index, 1)
	}
}

// 关闭所有菜单
const closeAll = () => {
	children.value.forEach(child => {
		if (child.close) {
			child.close()
		}
	})
}

// 自动关闭其他菜单（当某个菜单打开时）
const closeOthers = (currentChild) => {
	children.value.forEach(child => {
		if (child !== currentChild && child.close) {
			child.close()
		}
	})
	openItem.value = currentChild
}

// 重置所有子组件
const reset = () => {
	children.value.forEach(child => {
		if (child.init) {
			child.init()
		}
	})
}

// 提供给子组件的方法
provide('swipeGroup', {
	addChild,
	removeChild,
	closeOthers,
	closeAll
})

// 暴露方法
defineExpose({
	closeAll,
	reset,
	children
})
</script>

<style scoped>
.z-swipe-group {
	width: 100%;
}
</style>
