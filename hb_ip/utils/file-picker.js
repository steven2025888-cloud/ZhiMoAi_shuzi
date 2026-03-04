/**
 * 跨平台文件选择器
 * H5: uni.chooseFile
 * MP-WEIXIN: uni.chooseMessageFile
 * APP-PLUS: DOM <input type="file"> + plus.io 持久化
 */

/**
 * 选择文件
 * @param {Object} options
 * @param {string} options.accept - MIME 类型，如 'audio/*'（APP-PLUS 用）
 * @param {string[]} options.extensions - 扩展名列表，如 ['.mp3','.wav']
 * @returns {Promise<{path: string, name: string}>}
 */
export function pickFile({ accept = '*/*', extensions = [] } = {}) {
  // #ifdef H5
  return new Promise((resolve, reject) => {
    uni.chooseFile({
      count: 1,
      extension: extensions,
      success(res) {
        if (res.tempFilePaths && res.tempFilePaths.length) {
          resolve({
            path: res.tempFilePaths[0],
            name: (res.tempFiles && res.tempFiles[0] && res.tempFiles[0].name) || '文件',
          })
        } else {
          reject(new Error('cancel'))
        }
      },
      fail: reject,
    })
  })
  // #endif

  // #ifdef MP-WEIXIN
  return new Promise((resolve, reject) => {
    uni.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: extensions,
      success(res) {
        if (res.tempFiles && res.tempFiles.length) {
          resolve({
            path: res.tempFiles[0].path,
            name: res.tempFiles[0].name || '文件',
          })
        } else {
          reject(new Error('cancel'))
        }
      },
      fail: reject,
    })
  })
  // #endif

  // #ifdef APP-PLUS
  return _pickFileApp(accept)
  // #endif
}

/** 选择音频文件 */
export function pickAudioFile() {
  return pickFile({
    accept: 'audio/*,.wav,.mp3,.m4a,.aac,.flac',
    extensions: ['.wav', '.mp3', '.m4a', '.aac', '.flac'],
  })
}

/** 选择视频文件 */
export function pickVideoFile() {
  return pickFile({
    accept: 'video/*,.mp4,.mov',
    extensions: ['.mp4', '.mov', '.avi', '.mkv'],
  })
}

// #ifdef APP-PLUS
/**
 * APP 端文件选择（通过 WebView 隐藏 input + plus.io 持久化）
 */
function _pickFileApp(accept) {
  return new Promise((resolve, reject) => {
    try {
      const input = document.createElement('input')
      input.type = 'file'
      input.accept = accept
      input.style.cssText = 'position:fixed;top:-9999px;left:0;opacity:0;z-index:-1;'
      document.body.appendChild(input)

      const cleanup = () => {
        if (document.body.contains(input)) document.body.removeChild(input)
      }

      input.addEventListener('change', function () {
        const file = this.files && this.files[0]
        cleanup()
        if (!file) { reject(new Error('cancel')); return }

        const fileName = file.name || 'file_' + Date.now()
        uni.showLoading({ title: '读取文件...' })

        const reader = new FileReader()
        reader.onerror = () => { uni.hideLoading(); reject(new Error('读取文件失败')) }
        reader.onload = () => {
          const saveName = 'pick_' + Date.now() + '_' + fileName
          plus.io.requestFileSystem(plus.io.PRIVATE_DOC, (fs) => {
            fs.root.getFile(saveName, { create: true }, (entry) => {
              entry.createWriter((writer) => {
                writer.onerror = () => { uni.hideLoading(); reject(new Error('保存文件失败')) }
                writer.onwriteend = () => {
                  uni.hideLoading()
                  resolve({ path: entry.toLocalURL(), name: fileName })
                }
                writer.write(new Blob([reader.result]))
              }, () => { uni.hideLoading(); reject(new Error('保存失败')) })
            }, () => { uni.hideLoading(); reject(new Error('文件处理失败')) })
          }, () => { uni.hideLoading(); reject(new Error('存储不可用')) })
        }
        reader.readAsArrayBuffer(file)
      })

      input.click()
    } catch (e) {
      console.error('[pickFile] APP端文件选择失败:', e)
      reject(new Error('APP端文件选择不可用，请使用录音功能'))
    }
  })
}
// #endif
