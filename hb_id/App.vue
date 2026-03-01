<script>
	// #ifdef APP-PLUS
	import { preloadCommonIcons } from '@/uni_modules/zhimo-ui/components/z-icon/preload.js'
	// #endif

	export default {
		onLaunch: function() {
			console.log('App Launch')

			// #ifdef APP-PLUS
			// 预加载常用图标，实现立即显示
			preloadCommonIcons({
				onProgress: (loaded, total) => {
					console.log(`[图标预加载] ${loaded}/${total}`)
				},
				onComplete: () => {
					console.log('[图标预加载] 完成')
				}
			})
			// #endif

			// 检查登录状态
			const licenseKey = uni.getStorageSync('zm_license_key')
			if (!licenseKey) {
				// 未登录，跳转到登录页（延迟确保页面已加载）
				setTimeout(() => {
					uni.redirectTo({ url: '/pages/login/login' })
				}, 100)
			}
		},
		onShow: function() {
			console.log('App Show')
		},
		onHide: function() {
			console.log('App Hide')
		}
	}
</script>

<style  lang="scss">
	/* 全局导入字体文件（必须在全局导入，scoped 中不生效） */
	@import "@/uni_modules/zhimo-ui/styles/fonts-local.css";
	@import "@/uni_modules/zhimo-ui/styles/app-font.css";

	@import "@/uni_modules/zhimo-ui/common/zhimo.scss";
	page{
		// background-color: #f1f4fa;
	}
	/*每个页面公共css */
</style>
