# z-cropper (fix10)

## 你反馈：手机端“只要滑动图片再裁剪，第一次空白，第二次正常”

这属于某些端的 canvas 纹理/渲染管线时序问题：
- draw 回调触发了，但纹理还没真正写入
- 立刻 canvasToTempFilePath 就会导出空白

本版 fix10 处理：
1) export 前固定等待 `exportDelay`（默认 80ms，可调）
2) 非 H5：先做一次 **预热 draw**（drawOnce）
3) 导出后用 `uni.getFileInfo` 检查文件大小
   - size < 1200B 基本就是空白/透明图
   - 自动再 draw + 再导出（exportRetry 次，默认 1 次）

你不想调参的话，默认已经足够稳；
如果某些机型还会偶发，可以把 exportDelay 提到 120，exportRetry 设 2。
