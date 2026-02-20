# -*- coding: utf-8 -*-
# lib_avatar.py — 数字人库管理（含行内删除按钮）

import os, re, json, shutil, time

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
AVATARS_DIR  = os.path.join(BASE_DIR, "avatars")
AVATARS_META = os.path.join(AVATARS_DIR, "meta.json")
os.makedirs(AVATARS_DIR, exist_ok=True)


def load_meta():
    if os.path.exists(AVATARS_META):
        try:
            with open(AVATARS_META, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_meta(data):
    try:
        with open(AVATARS_META, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_choices():
    items = [m for m in load_meta() if m.get("path") and os.path.exists(m.get("path", ""))]
    return [m["name"] for m in items] if items else ["（暂无数字人，请先添加）"]


def get_path(name):
    for m in load_meta():
        if m.get("name") == name:
            p = m.get("path", "")
            return p if os.path.exists(p) else None
    return None


def add_avatar(video_path, name):
    if not video_path or not os.path.exists(str(video_path)):
        return False, "请先上传视频"
    name = (name or "").strip()
    if not name:
        return False, "请输入数字人名称"
    for m in load_meta():
        if m.get("name") == name:
            return False, f"名称「{name}」已存在"
    ext  = os.path.splitext(str(video_path))[1] or ".mp4"
    ts   = int(time.time())
    safe = re.sub(r'[\\/:*?"<>|]', '_', name)
    dst  = os.path.join(AVATARS_DIR, f"{safe}_{ts}{ext}")
    try:
        shutil.copy2(str(video_path), dst)
    except Exception as e:
        return False, f"保存失败: {e}"
    meta = load_meta()
    meta.append({"name": name, "path": dst, "time": time.strftime("%Y-%m-%d %H:%M")})
    save_meta(meta)
    return True, f"数字人「{name}」已保存"


def del_avatar(name):
    if not name or name.startswith("（"):
        return False, "请选择要删除的数字人"
    meta = load_meta()
    new_meta, deleted = [], False
    for m in meta:
        if m.get("name") == name:
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
        save_meta(new_meta)
        print(f"[删除] 已保存元数据，剩余 {len(new_meta)} 个数字人")
        print(f"[删除] 元数据文件: {AVATARS_META}")
        return True, f"已删除「{name}」"
    return False, "未找到该数字人"


def render_gallery(del_trigger_id="av-del-input"):
    """
    渲染数字人卡片 HTML。
    每张卡片末尾有一个删除按钮，点击时弹窗确认后再删除。
    """
    meta = load_meta()
    if not meta:
        return (
            '<div style="text-align:center;padding:48px 20px;color:#94a3b8;">'
            '<div style="font-size:44px;margin-bottom:14px;">🎭</div>'
            '<div style="font-size:13px;font-weight:600;">暂无数字人</div>'
            '<div style="font-size:11px;margin-top:4px;">在左侧上传视频并保存</div>'
            '</div>'
        )

    cards = ""
    for m in meta:
        name  = m.get("name", "未命名")
        path  = m.get("path", "")
        t     = m.get("time", "")
        exist = os.path.exists(path) if path else False
        dot   = "#22c55e" if exist else "#ef4444"
        sz    = ""
        if exist:
            try:
                sz = f" · {os.path.getsize(path)/1048576:.1f}MB"
            except Exception:
                pass
        # JS：使用自定义删除对话框
        name_escaped = name.replace('\\', '\\\\').replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
        js_click = f"window._zdaiTriggerDel('{del_trigger_id}','{name_escaped}','avatar');"
        cards += f"""
<div style="display:flex;align-items:center;gap:12px;
  background:#fff;border:1.5px solid #e5e7eb;border-radius:12px;
  padding:10px 14px;margin-bottom:8px;
  box-shadow:0 1px 4px rgba(0,0,0,.04);
  transition:border-color .15s;">
  <div style="width:44px;height:44px;border-radius:10px;flex-shrink:0;
    background:linear-gradient(135deg,#6366f1,#8b5cf6);
    display:flex;align-items:center;justify-content:center;font-size:20px;">🎭</div>
  <div style="flex:1;min-width:0;">
    <div style="font-size:14px;font-weight:700;color:#0f172a;
      overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{name}</div>
    <div style="font-size:11px;color:#94a3b8;margin-top:2px;display:flex;align-items:center;gap:5px;">
      <span style="width:7px;height:7px;border-radius:50%;background:{dot};display:inline-block;"></span>
      {os.path.basename(path) if path else "未知"}{sz}
    </div>
    <div style="font-size:10px;color:#cbd5e1;margin-top:1px;">{t}</div>
  </div>
  <button onclick="{js_click}" title="删除此数字人"
    style="flex-shrink:0;width:32px;height:32px;border-radius:8px;
      border:1.5px solid #fecdd3;background:#fff1f2;color:#dc2626;
      font-size:16px;cursor:pointer;display:flex;align-items:center;
      justify-content:center;transition:all .15s;"
    onmouseover="this.style.background='#dc2626';this.style.color='#fff';"
    onmouseout="this.style.background='#fff1f2';this.style.color='#dc2626';">
    🗑
  </button>
</div>"""

    return f'<div style="max-height:420px;overflow-y:auto;padding-right:2px;">{cards}</div>'