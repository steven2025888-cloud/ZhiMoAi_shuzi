/**
 * 调用后端 API 提取视频
 * POST http://localhost:5000/api/extract-and-parse
 */

export function extractVideo(text) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: 'http://localhost:5000/api/extract-and-parse',
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: { text },
      timeout: 30000,
      success(res) {
        if (res.statusCode === 200) {
          resolve(res.data)
        } else {
          reject(new Error(`HTTP ${res.statusCode}`))
        }
      },
      fail(err) {
        reject(err)
      }
    })
  })
}
