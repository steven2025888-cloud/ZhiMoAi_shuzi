# -*- coding: utf-8 -*-
"""
lib_voice.py — 音色库管理

支持本地版和在线版音色管理。
"""

import json
import os
import re
import shutil
import time
from typing import Dict, List, Optional, Tuple, Any

from voice_api import API_BASE_URL

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================================
# 常量
# ============================================================
META_SAVE_RETRIES = 3


class VoiceStore:
    """音色库管理（支持本地版和在线版）"""
    
    def __init__(self):
        self.store_dir = os.path.join(BASE_DIR, "voices")
        self.meta_path = os.path.join(self.store_dir, "meta.json")
        os.makedirs(self.store_dir, exist_ok=True)
    
    # ============================================================
    # 元数据存储
    # ============================================================
    def load_meta(self) -> List[Dict[str, Any]]:
        """加载元数据"""
        if not os.path.exists(self.meta_path):
            return []
        try:
            with open(self.meta_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    
    def save_meta(self, data: List[Dict[str, Any]]) -> bool:
        """保存元数据，带重试和验证"""
        content = json.dumps(data, ensure_ascii=False, indent=2)
        
        for attempt in range(META_SAVE_RETRIES):
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
    def _get_valid_items(self) -> List[Dict[str, Any]]:
        """获取所有有效的音色项"""
        items = []
        for m in self.load_meta():
            source = m.get("source", "local")
            if source == "online":
                items.append(m)
            else:
                path = m.get("path", "")
                if path and os.path.exists(path):
                    items.append(m)
        return items
    
    def _format_display_name(self, item: Dict[str, Any]) -> str:
        """格式化显示名称"""
        name = item.get("name", "")
        source = item.get("source", "local")
        return f"☁️ {name}" if source == "online" else f"💻 {name}"
    
    def _parse_display_name(self, display_name: str) -> str:
        """从显示名称提取实际名称"""
        if not display_name or display_name.startswith("（"):
            return ""
        # 去掉前缀标识
        for prefix in ("☁️ ", "💻 "):
            if display_name.startswith(prefix):
                return display_name[len(prefix):]
        return display_name
    
    def get_choices(self, filter_mode: str = None) -> List[str]:
        """返回音色选项列表，带版本标识
        
        Args:
            filter_mode: 过滤模式，'local'只显示本地音色，'online'只显示在线音色，None显示全部
        """
        items = self._get_valid_items()
        
        # 根据模式过滤
        if filter_mode == "local":
            items = [m for m in items if m.get("source", "local") == "local"]
        elif filter_mode == "online":
            items = [m for m in items if m.get("source", "local") == "online"]
        
        if items:
            return [self._format_display_name(m) for m in items]
        
        # 根据模式返回不同的提示
        if filter_mode == "local":
            return ["（暂无本地音色，请先添加）"]
        elif filter_mode == "online":
            return ["（暂无在线音色，请先上传）"]
        return ["（暂无音色，请先添加）"]
    
    def get_voice_info(self, display_name: str) -> Optional[Dict[str, Any]]:
        """根据显示名称获取音色完整信息"""
        clean_name = self._parse_display_name(display_name)
        if not clean_name:
            return None
        
        for m in self.load_meta():
            if m.get("name") == clean_name:
                return m
        return None
    
    def get_path(self, display_name: str) -> Optional[str]:
        """获取本地版音色的文件路径"""
        info = self.get_voice_info(display_name)
        if info and info.get("source", "local") == "local":
            path = info.get("path", "")
            return path if os.path.exists(path) else None
        return None
    
    def is_online(self, display_name: str) -> bool:
        """判断音色是否为在线版"""
        info = self.get_voice_info(display_name)
        return bool(info and info.get("source") == "online")
    
    def get_online_model_id(self, display_name: str) -> Optional[int]:
        """获取在线版音色的 model_id"""
        info = self.get_voice_info(display_name)
        if info and info.get("source") == "online":
            return info.get("model_id")
        return None
    
    def add_local_voice(self, file_path, name: str) -> tuple:
        """添加本地版音色"""
        if not file_path or not os.path.exists(str(file_path)):
            return False, "请先上传音频"
        name = (name or "").strip()
        if not name:
            return False, "请输入音色名称"
        for m in self.load_meta():
            if m.get("name") == name:
                return False, f"名称「{name}」已存在"
        
        ext = os.path.splitext(str(file_path))[1] or ".wav"
        ts = int(time.time())
        safe = re.sub(r'[\\/:*?"<>|]', '_', name)
        dst = os.path.join(self.store_dir, f"{safe}_{ts}{ext}")
        try:
            shutil.copy2(str(file_path), dst)
        except Exception as e:
            return False, f"保存失败: {e}"
        
        meta = self.load_meta()
        meta.append({
            "name": name,
            "path": dst,
            "source": "local",
            "time": time.strftime("%Y-%m-%d %H:%M")
        })
        self.save_meta(meta)
        return True, f"本地音色「{name}」已保存"
    
    def add_online_voice(self, file_path, name: str) -> tuple:
        """添加在线版音色（上传到服务器）"""
        print(f"[add_online_voice] 开始上传，file_path={file_path}, name={name}")
        if not file_path or not os.path.exists(str(file_path)):
            return False, "请先上传音频"
        name = (name or "").strip()
        if not name:
            return False, "请输入音色名称"
        for m in self.load_meta():
            if m.get("name") == name:
                return False, f"名称「{name}」已存在"
        
        # 获取卡密和调用 API
        try:
            from voice_api import VoiceApiClient, API_BASE_URL
            from lib_license import check_saved_license
            
            print(f"[add_online_voice] API_BASE_URL={API_BASE_URL}")
            
            status, info = check_saved_license()
            print(f"[add_online_voice] 卡密状态: status={status}")
            if status != "valid":
                return False, "请先登录卡密后再使用在线版"
            
            license_key = info.get("license_key", "")
            if not license_key:
                return False, "卡密无效，请重新登录"
            
            # API 基地址
            client = VoiceApiClient(API_BASE_URL, license_key)
            
            # 上传模型
            print(f"[add_online_voice] 正在调用 upload_model...")
            result = client.upload_model(file_path, name, describe="")
            print(f"[add_online_voice] 服务器返回: {result}")
            if result.get("code") == 0:
                data = result.get("data", {})
                # 兼容服务器返回 id 或 model_id
                model_id = data.get("model_id") or data.get("id")
                audio_id = data.get("audio_id", "")
                
                if model_id:
                    # 保存到本地 meta（不保存文件，只记录 model_id 和 audio_id）
                    meta = self.load_meta()
                    meta.append({
                        "name": name,
                        "source": "online",
                        "model_id": model_id,
                        "audio_id": audio_id,  # 保存 audio_id 以便后续使用
                        "time": time.strftime("%Y-%m-%d %H:%M")
                    })
                    self.save_meta(meta)
                    print(f"[add_online_voice] 保存成功: model_id={model_id}, audio_id={audio_id}")
                    return True, f"在线音色「{name}」已上传"
                else:
                    return False, "服务器返回的 model_id 无效"
            else:
                msg = result.get("msg", "上传失败")
                return False, f"上传失败：{msg}"
        except ImportError as e:
            return False, f"缺少依赖模块：{e}"
        except Exception as e:
            return False, f"上传失败：{e}"
    
    def add_item(self, file_path, name: str, source: str = "local") -> tuple:
        """添加音色（兼容旧接口）"""
        if source == "online":
            return self.add_online_voice(file_path, name)
        else:
            return self.add_local_voice(file_path, name)
    
    def del_item(self, display_name: str) -> tuple:
        """删除音色"""
        if not display_name or display_name.startswith("（"):
            return False, "请选择要删除的音色"
        
        # 获取实际名称
        info = self.get_voice_info(display_name)
        if not info:
            return False, "未找到该音色"
        
        name = info.get("name")
        source = info.get("source", "local")
        
        # 如果是在线版，需要调用 API 删除
        if source == "online":
            try:
                from voice_api import VoiceApiClient, API_BASE_URL
                from lib_license import check_saved_license
                
                status, lic_info = check_saved_license()
                if status == "valid":
                    license_key = lic_info.get("license_key", "")
                    client = VoiceApiClient(API_BASE_URL, license_key)
                    model_id = info.get("model_id")
                    if model_id:
                        result = client.delete_model(model_id)
                        if result.get("code") != 0:
                            print(f"[删除] 服务器删除失败: {result.get('msg')}")
            except Exception as e:
                print(f"[删除] 在线删除失败: {e}")
        
        # 删除本地元数据和文件
        meta = self.load_meta()
        new_meta, deleted = [], False
        for m in meta:
            if m.get("name") == name:
                if source == "local":
                    try:
                        p = m.get("path", "")
                        if p and os.path.exists(p):
                            os.remove(p)
                            print(f"[删除] 已删除文件: {p}")
                    except Exception as e:
                        print(f"[删除] 删除文件失败: {e}")
                deleted = True
            else:
                new_meta.append(m)
        
        if deleted:
            self.save_meta(new_meta)
            return True, f"已删除「{name}」"
        return False, "未找到该音色"
    
    def sync_online_voices(self) -> tuple:
        """从服务器同步在线音色列表"""
        try:
            from voice_api import VoiceApiClient, API_BASE_URL
            from lib_license import check_saved_license
            
            status, info = check_saved_license()
            if status != "valid":
                return False, "请先登录卡密"
            
            license_key = info.get("license_key", "")
            client = VoiceApiClient(API_BASE_URL, license_key)
            
            result = client.list_models()
            if result.get("code") == 0:
                server_models = result.get("data", [])
                
                # 读取本地 meta
                meta = self.load_meta()
                
                # 保留本地版和已存在的在线版
                local_voices = [m for m in meta if m.get("source", "local") == "local"]
                online_names = {m.get("name") for m in meta if m.get("source") == "online"}
                
                # 从服务器列表添加新的在线版
                for model in server_models:
                    model_name = model.get("name", "")
                    model_id = model.get("id")
                    if model_name and model_name not in online_names:
                        local_voices.append({
                            "name": model_name,
                            "source": "online",
                            "model_id": model_id,
                            "time": time.strftime("%Y-%m-%d %H:%M")
                        })
                
                self.save_meta(local_voices)
                return True, f"同步成功，共 {len(server_models)} 个在线音色"
            else:
                return False, result.get("msg", "同步失败")
        except Exception as e:
            return False, f"同步失败：{e}"
    
    def render_gallery(self, del_trigger_id: str = "vc-del-input",
                       preview_trigger_id: str = "vc-prev-trigger") -> str:
        """渲染音色库画廊（带版本标识）"""
        meta = self.load_meta()
        if not meta:
            return (
                '<div style="text-align:center;padding:56px 20px;color:#94a3b8;'
                'background:linear-gradient(135deg,#f8fafc,#f1f5f9);border-radius:16px;'
                'border:2px dashed #e2e8f0;">'
                '<div style="font-size:52px;margin-bottom:16px;filter:grayscale(.3);">🎙</div>'
                '<div style="font-size:14px;font-weight:700;color:#64748b;">暂无音色</div>'
                '<div style="font-size:12px;margin-top:6px;color:#94a3b8;">在左侧上传音频并保存即可添加</div>'
                '</div>'
            )
        
        cards = ""
        for idx, m in enumerate(meta):
            name = m.get("name", "未命名")
            source = m.get("source", "local")
            path = m.get("path", "")
            t = m.get("time", "")
            
            # 版本标识
            if source == "online":
                source_badge = '<span style="background:#dbeafe;color:#1d4ed8;font-size:10px;padding:2px 6px;border-radius:4px;font-weight:600;">☁️ 在线版</span>'
                exist = True  # 在线版不需要检查本地文件
                sz = ""
            else:
                source_badge = '<span style="background:#dcfce7;color:#15803d;font-size:10px;padding:2px 6px;border-radius:4px;font-weight:600;">💻 本地版</span>'
                exist = os.path.exists(path) if path else False
                sz = ""
                if exist:
                    try:
                        sz = f" · {os.path.getsize(path)/1048576:.1f}MB"
                    except Exception:
                        pass
            
            dot = "#22c55e" if exist else "#ef4444"
            status_text = "可用" if exist else "文件丢失"
            
            # 显示名称用于 JS
            if source == "online":
                display_name = f"☁️ {name}"
            else:
                display_name = f"💻 {name}"
            
            name_escaped = (display_name.replace('\\', '\\\\').replace("'", "\\'")
                            .replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r'))
            js_del = (f"event.stopPropagation();"
                      f"window._zdaiTriggerDel('{del_trigger_id}','{name_escaped}','voice');")
            js_preview = f"window._zdaiTriggerPreview('{preview_trigger_id}','{name_escaped}');" if source == "local" else ""
            bg = "#fff" if idx % 2 == 0 else "#fafbfc"
            
            cursor = "cursor:pointer;" if source == "local" else "cursor:default;"
            
            cards += f"""
<div onclick="{js_preview}" style="display:flex;align-items:center;gap:14px;
  background:{bg};border:1.5px solid #e5e7eb;border-radius:14px;
  padding:12px 16px;margin-bottom:8px;{cursor}
  box-shadow:0 1px 4px rgba(0,0,0,.03);
  transition:all .2s ease;"
  onmouseover="this.style.borderColor='#7dd3fc';this.style.boxShadow='0 4px 12px rgba(14,165,233,.1)'"
  onmouseout="this.style.borderColor='#e5e7eb';this.style.boxShadow='0 1px 4px rgba(0,0,0,.03)'">
  <div style="width:46px;height:46px;border-radius:12px;flex-shrink:0;
    background:linear-gradient(135deg,#0ea5e9,#0284c7);
    display:flex;align-items:center;justify-content:center;font-size:22px;
    box-shadow:0 2px 8px rgba(14,165,233,.25);">🎙</div>
  <div style="flex:1;min-width:0;">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:3px;">
      <span style="font-size:14px;font-weight:700;color:#0f172a;
        overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{name}</span>
      {source_badge}
    </div>
    <div style="font-size:11px;color:#94a3b8;display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
      <span style="display:inline-flex;align-items:center;gap:3px;">
        <span style="width:6px;height:6px;border-radius:50%;background:{dot};display:inline-block;"></span>
        <span style="color:{dot};font-weight:600;">{status_text}</span>
      </span>
      <span style="color:#cbd5e1;">|</span>
      <span>{os.path.basename(path) if path else "云端存储"}{sz}</span>
    </div>
    <div style="font-size:10px;color:#cbd5e1;margin-top:2px;">📅 {t}</div>
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
</div>"""
        
        count = len(meta)
        local_count = sum(1 for m in meta if m.get("source", "local") == "local")
        online_count = count - local_count
        header = (
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'margin-bottom:10px;padding:0 2px;">'
            f'<span style="font-size:12px;color:#64748b;font-weight:600;">'
            f'共 {count} 个音色（💻本地 {local_count} · ☁️在线 {online_count}）</span>'
            f'<span style="font-size:11px;color:#94a3b8;">点击本地版试听 · 点击 🗑 删除</span>'
            f'</div>'
        )
        return f'{header}<div style="max-height:420px;overflow-y:auto;padding-right:2px;">{cards}</div>'


_store = VoiceStore()

# ── 向后兼容的模块级函数 ──
load_meta      = _store.load_meta
save_meta      = _store.save_meta
get_choices    = _store.get_choices
get_path       = _store.get_path
get_voice_info = _store.get_voice_info
is_online      = _store.is_online
get_online_model_id = _store.get_online_model_id
add_voice      = _store.add_item
add_local_voice = _store.add_local_voice
add_online_voice = _store.add_online_voice
del_voice      = _store.del_item
render_gallery = _store.render_gallery
sync_online_voices = _store.sync_online_voices
