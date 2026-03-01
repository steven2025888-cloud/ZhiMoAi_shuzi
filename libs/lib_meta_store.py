# -*- coding: utf-8 -*-
"""
lib_meta_store.py — 资源库通用基类

提供数字人、音色等资源的统一管理能力，包括：
- 资源的增删查
- 元数据存储
- 卡片式UI渲染
"""

import json
import os
import re
import shutil
import time
from typing import List, Optional, Tuple, Dict, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class MetaStore:
    """
    通用资源库管理基类
    
    子类只需覆盖配置属性即可获得完整的资源管理能力。
    """

    # 子类配置属性
    store_dir_name: str = ""          # 存储目录名
    item_label: str = "项目"           # 显示名称
    upload_label: str = "文件"         # 上传提示
    default_ext: str = ".mp4"         # 默认扩展名
    empty_icon: str = "📁"            # 空状态图标
    card_icon: str = "📁"             # 卡片图标
    card_gradient: str = "linear-gradient(135deg,#6366f1,#8b5cf6)"
    card_shadow: str = "rgba(99,102,241,.25)"
    card_hover_border: str = "#a5b4fc"
    card_hover_shadow: str = "rgba(99,102,241,.1)"
    del_type: str = "item"            # JS删除类型标识
    
    # 元数据保存重试次数
    META_SAVE_RETRIES: int = 3

    def __init__(self):
        self.store_dir = os.path.join(BASE_DIR, self.store_dir_name)
        self.meta_path = os.path.join(self.store_dir, "meta.json")
        os.makedirs(self.store_dir, exist_ok=True)

    # ============================================================
    # 元数据存储
    # ============================================================
    def load_meta(self) -> List[Dict[str, Any]]:
        """加载元数据列表"""
        if not os.path.exists(self.meta_path):
            return []
        try:
            with open(self.meta_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def save_meta(self, data: List[Dict[str, Any]]) -> bool:
        """
        保存元数据列表，带重试和验证
        
        Returns:
            保存是否成功
        """
        content = json.dumps(data, ensure_ascii=False, indent=2)
        
        for attempt in range(self.META_SAVE_RETRIES):
            try:
                with open(self.meta_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                
                # 验证保存结果
                with open(self.meta_path, 'r', encoding='utf-8') as f:
                    if len(json.load(f)) == len(data):
                        return True
            except (IOError, json.JSONDecodeError) as e:
                print(f"[save_meta] 第{attempt + 1}次尝试失败: {e}")
                time.sleep(0.1)
        
        return False

    # ============================================================
    # 查询方法
    # ============================================================
    def get_choices(self) -> List[str]:
        """获取可用资源名称列表（用于下拉选项）"""
        valid_items = [
            m["name"] for m in self.load_meta()
            if m.get("path") and os.path.exists(m.get("path", ""))
        ]
        return valid_items if valid_items else [f"（暂无{self.item_label}，请先添加）"]

    def get_path(self, name: str) -> Optional[str]:
        """根据名称获取资源文件路径"""
        for m in self.load_meta():
            if m.get("name") == name:
                path = m.get("path", "")
                return path if os.path.exists(path) else None
        return None

    # ============================================================
    # 增删操作
    # ============================================================
    def _sanitize_filename(self, name: str) -> str:
        """清理文件名中的非法字符"""
        return re.sub(r'[\\/:*?"<>|]', '_', name)

    def add_item(self, file_path: Optional[str], name: str) -> Tuple[bool, str]:
        """
        添加资源
        
        Args:
            file_path: 源文件路径
            name: 资源名称
            
        Returns:
            (是否成功, 消息)
        """
        # 验证输入
        if not file_path or not os.path.exists(str(file_path)):
            return False, f"请先上传{self.upload_label}"
        
        name = (name or "").strip()
        if not name:
            return False, f"请输入{self.item_label}名称"
        
        # 检查名称是否重复
        if any(m.get("name") == name for m in self.load_meta()):
            return False, f"名称「{name}」已存在"
        
        # 生成目标路径
        ext = os.path.splitext(str(file_path))[1] or self.default_ext
        safe_name = self._sanitize_filename(name)
        dst = os.path.join(self.store_dir, f"{safe_name}_{int(time.time())}{ext}")
        
        # 复制文件
        try:
            shutil.copy2(str(file_path), dst)
        except (IOError, shutil.Error) as e:
            return False, f"保存失败: {e}"
        
        # 更新元数据
        meta = self.load_meta()
        meta.append({
            "name": name,
            "path": dst,
            "time": time.strftime("%Y-%m-%d %H:%M")
        })
        self.save_meta(meta)
        
        return True, f"{self.item_label}「{name}」已保存"

    def del_item(self, name: str) -> Tuple[bool, str]:
        """
        删除资源
        
        Args:
            name: 资源名称
            
        Returns:
            (是否成功, 消息)
        """
        if not name or name.startswith("（"):
            return False, f"请选择要删除的{self.item_label}"
        
        meta = self.load_meta()
        new_meta = []
        deleted = False
        
        for m in meta:
            if m.get("name") == name:
                # 删除文件
                path = m.get("path", "")
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                        print(f"[删除] 已删除文件: {path}")
                    except OSError as e:
                        print(f"[删除] 删除文件失败: {e}")
                deleted = True
            else:
                new_meta.append(m)
        
        if not deleted:
            return False, f"未找到该{self.item_label}"
        
        # 保存并验证
        self.save_meta(new_meta)
        
        # 验证删除结果
        if any(m.get("name") == name for m in self.load_meta()):
            print(f"[删除] [警告] 验证失败，强制重写")
            self.save_meta(new_meta)
        else:
            print(f"[删除] [OK] 剩余 {len(new_meta)} 个{self.item_label}")
        
        return True, f"已删除「{name}」"

    # ============================================================
    # UI渲染
    # ============================================================
    def _escape_js_string(self, s: str) -> str:
        """转义JS字符串"""
        return (s.replace('\\', '\\\\')
                 .replace("'", "\\'")
                 .replace('"', '\\"')
                 .replace('\n', '\\n')
                 .replace('\r', '\\r'))

    def _get_file_size_mb(self, path: str) -> Optional[float]:
        """获取文件大小(MB)"""
        try:
            return os.path.getsize(path) / 1048576
        except OSError:
            return None

    def _render_empty_state(self) -> str:
        """渲染空状态UI"""
        return (
            f'<div style="text-align:center;padding:56px 20px;color:#94a3b8;'
            f'background:linear-gradient(135deg,#f8fafc,#f1f5f9);border-radius:16px;'
            f'border:2px dashed #e2e8f0;">'
            f'<div style="font-size:52px;margin-bottom:16px;filter:grayscale(.3);">{self.empty_icon}</div>'
            f'<div style="font-size:14px;font-weight:700;color:#64748b;">暂无{self.item_label}</div>'
            f'<div style="font-size:12px;margin-top:6px;color:#94a3b8;">在左侧上传{self.upload_label}并保存即可添加</div>'
            f'</div>'
        )

    def _render_card(self, item: Dict[str, Any], idx: int, 
                     del_trigger_id: str, preview_trigger_id: str) -> str:
        """渲染单个资源卡片"""
        name = item.get("name", "未命名")
        path = item.get("path", "")
        create_time = item.get("time", "")
        
        # 状态信息
        exists = os.path.exists(path) if path else False
        status_color = "#22c55e" if exists else "#ef4444"
        status_text = "可用" if exists else "文件丢失"
        
        # 文件大小
        size_str = ""
        if exists:
            size_mb = self._get_file_size_mb(path)
            if size_mb is not None:
                size_str = f" · {size_mb:.1f}MB"
        
        # JS事件
        name_escaped = self._escape_js_string(name)
        js_del = (f"event.stopPropagation();"
                  f"window._zdaiTriggerDel('{del_trigger_id}','{name_escaped}','{self.del_type}');")
        js_preview = f"window._zdaiTriggerPreview('{preview_trigger_id}','{name_escaped}');"
        
        bg = "#fff" if idx % 2 == 0 else "#fafbfc"
        filename = os.path.basename(path) if path else "未知"

        return f'''
<div onclick="{js_preview}" style="display:flex;align-items:center;gap:14px;
  background:{bg};border:1.5px solid #e5e7eb;border-radius:14px;
  padding:12px 16px;margin-bottom:8px;cursor:pointer;
  box-shadow:0 1px 4px rgba(0,0,0,.03);transition:all .2s ease;"
  onmouseover="this.style.borderColor='{self.card_hover_border}';this.style.boxShadow='0 4px 12px {self.card_hover_shadow}'"
  onmouseout="this.style.borderColor='#e5e7eb';this.style.boxShadow='0 1px 4px rgba(0,0,0,.03)'">
  <div style="width:46px;height:46px;border-radius:12px;flex-shrink:0;
    background:{self.card_gradient};
    display:flex;align-items:center;justify-content:center;font-size:22px;
    box-shadow:0 2px 8px {self.card_shadow};">{self.card_icon}</div>
  <div style="flex:1;min-width:0;">
    <div style="font-size:14px;font-weight:700;color:#0f172a;
      overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
      margin-bottom:3px;">{name}</div>
    <div style="font-size:11px;color:#94a3b8;display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
      <span style="display:inline-flex;align-items:center;gap:3px;">
        <span style="width:6px;height:6px;border-radius:50%;background:{status_color};display:inline-block;"></span>
        <span style="color:{status_color};font-weight:600;">{status_text}</span>
      </span>
      <span style="color:#cbd5e1;">|</span>
      <span>{filename}{size_str}</span>
    </div>
    <div style="font-size:10px;color:#cbd5e1;margin-top:2px;">📅 {create_time}</div>
  </div>
  <button onclick="{js_del}" title="删除「{name}」"
    style="flex-shrink:0;width:34px;height:34px;border-radius:10px;
      border:1.5px solid #fecdd3;background:#fff1f2;color:#e11d48;
      font-size:15px;cursor:pointer;display:flex;align-items:center;
      justify-content:center;transition:all .2s;
      box-shadow:0 1px 3px rgba(225,29,72,.08);"
    onmouseover="this.style.background='#e11d48';this.style.color='#fff';this.style.borderColor='#e11d48';this.style.boxShadow='0 4px 12px rgba(225,29,72,.25)'"
    onmouseout="this.style.background='#fff1f2';this.style.color='#e11d48';this.style.borderColor='#fecdd3';this.style.boxShadow='0 1px 3px rgba(225,29,72,.08)'">
    🗑
  </button>
</div>'''

    def render_gallery(self, del_trigger_id: str = "del-input",
                       preview_trigger_id: str = "prev-trigger") -> str:
        """
        渲染资源卡片列表
        
        Args:
            del_trigger_id: 删除触发器ID
            preview_trigger_id: 预览触发器ID
            
        Returns:
            HTML字符串
        """
        meta = self.load_meta()
        if not meta:
            return self._render_empty_state()

        # 渲染所有卡片
        cards = "".join(
            self._render_card(item, idx, del_trigger_id, preview_trigger_id)
            for idx, item in enumerate(meta)
        )
        
        # 头部信息
        header = (
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'margin-bottom:10px;padding:0 2px;">'
            f'<span style="font-size:12px;color:#64748b;font-weight:600;">共 {len(meta)} 个{self.item_label}</span>'
            f'<span style="font-size:11px;color:#94a3b8;">点击卡片预览 · 点击 🗑 删除</span>'
            f'</div>'
        )
        
        return f'{header}<div style="max-height:420px;overflow-y:auto;padding-right:2px;">{cards}</div>'
