# 语音合成 + 口型同步 统一工作台

## 目录结构

```
你的目录/
├── IndexTTS2-SonicVale/     ← 已有的 IndexTTS2 项目
│   ├── webui.py
│   ├── checkpoints/
│   ├── installer_files/     ← Conda 环境
│   └── ...
├── LatentSync/              ← 已有的 LatentSync 项目
│   ├── gradio_app.py
│   ├── latents_env/         ← LatentSync 的 Python 环境
│   └── ...
├── unified_app.py           ← 本程序
├── 启动统一界面.bat          ← 双击启动
└── README.md
```

## 使用方法

1. 将 `unified_app.py` 和 `启动统一界面.bat` 放到 `IndexTTS2-SonicVale` 和 `LatentSync` 的 **同级目录**
2. 双击 `启动统一界面.bat` 启动
3. 浏览器会自动打开 `http://localhost:7870`

## 工作流程

1. **加载模型** — 点击「加载模型」按钮加载 IndexTTS2
2. **语音合成** — 输入文本 → 上传音色参考音频 → 调整情感 → 点击「生成语音」
3. **口型同步** — 上传视频 → 音频会自动填入 → 点击「生成口型同步视频」

## 需要注意

### LatentSync 调用方式

由于 LatentSync 使用独立的 Python 环境，本程序通过 `subprocess` 调用它。程序会自动尝试以下入口：

- `inference.py`
- `run_inference.py`
- `scripts/inference.py`
- `gradio_app.py` 中的 `process_video` 函数

**如果以上都不匹配你的 LatentSync 版本**，请修改 `unified_app.py` 中 `run_latentsync` 函数里的调用逻辑。

### 常见问题

- **目录名不同？** 修改 `unified_app.py` 顶部的 `INDEXTTS_DIR` 和 `LATENTSYNC_DIR`
- **端口冲突？** 运行 `启动统一界面.bat` 后修改为 `python unified_app.py --port 7890`
- **需要公网访问？** 添加 `--share` 参数
