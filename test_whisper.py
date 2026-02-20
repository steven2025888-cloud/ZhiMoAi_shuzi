# -*- coding: utf-8 -*-
"""
Whisper 语音识别测试脚本
用于测试 Whisper 是否正常工作
"""

import os
import sys

# 添加路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

def test_whisper_import():
    """测试 Whisper 导入"""
    print("=" * 60)
    print("测试 1: 导入 Whisper 模块")
    print("=" * 60)
    try:
        import whisper
        print(f"✓ Whisper 版本: {whisper.__version__}")
        print(f"✓ 可用模型: {', '.join(whisper.available_models())}")
        return True
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        return False


def test_load_model():
    """测试加载模型"""
    print("\n" + "=" * 60)
    print("测试 2: 加载 Whisper 模型（tiny）")
    print("=" * 60)
    print("提示：首次运行会下载模型文件（约 39MB），请耐心等待...")
    try:
        import whisper
        model = whisper.load_model("tiny")
        print("✓ 模型加载成功")
        return model
    except Exception as e:
        print(f"✗ 模型加载失败: {e}")
        return None


def test_transcribe():
    """测试转录功能"""
    print("\n" + "=" * 60)
    print("测试 3: 测试音频转录")
    print("=" * 60)
    
    # 查找测试音频
    test_audio = None
    possible_paths = [
        "IndexTTS2-SonicVale/examples/voice_01.wav",
        "LatentSync/assets/demo1_audio.wav",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            test_audio = path
            break
    
    if not test_audio:
        print("⚠ 未找到测试音频文件，跳过转录测试")
        print("  可以手动测试：")
        print("  model = whisper.load_model('tiny')")
        print("  result = model.transcribe('your_audio.wav')")
        return
    
    print(f"使用测试音频: {test_audio}")
    
    try:
        import whisper
        model = whisper.load_model("tiny")
        print("正在转录音频...")
        result = model.transcribe(test_audio, language="zh", fp16=False)
        
        print("\n转录结果:")
        print("-" * 60)
        print(result["text"])
        print("-" * 60)
        
        if result.get("segments"):
            print("\n分段结果:")
            for i, segment in enumerate(result["segments"][:3], 1):  # 只显示前3段
                print(f"  [{segment['start']:.2f}s - {segment['end']:.2f}s] {segment['text']}")
            if len(result["segments"]) > 3:
                print(f"  ... 还有 {len(result['segments']) - 3} 段")
        
        print("\n✓ 转录测试成功")
        
    except Exception as e:
        print(f"✗ 转录失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "Whisper 功能测试" + " " * 26 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    # 测试 1: 导入
    if not test_whisper_import():
        print("\n✗ Whisper 未正确安装")
        print("请运行: IndexTTS2-SonicVale\\installer_files\\env\\python.exe -m pip install openai-whisper")
        return
    
    # 测试 2: 加载模型
    model = test_load_model()
    if not model:
        print("\n✗ 模型加载失败")
        return
    
    # 测试 3: 转录
    test_transcribe()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n✓ Whisper 已正确安装并可以使用")
    print("\n使用方法:")
    print("  1. 查看 'Whisper使用说明.txt' 了解详细用法")
    print("  2. 在 Python 中导入: import whisper")
    print("  3. 加载模型: model = whisper.load_model('base')")
    print("  4. 转录音频: result = model.transcribe('audio.mp3')")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n按任意键退出...")
        input()
