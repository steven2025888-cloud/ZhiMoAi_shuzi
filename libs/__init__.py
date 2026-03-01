# -*- coding: utf-8 -*-
# libs/ 包初始化
# 将 libs/ 目录加入 sys.path，使内部模块间的 import 保持兼容
import os, sys
_LIBS_DIR = os.path.dirname(os.path.abspath(__file__))
if _LIBS_DIR not in sys.path:
    sys.path.insert(0, _LIBS_DIR)
