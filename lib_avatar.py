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
    """保存 meta.json"""
    content = json.dumps(data, ensure_ascii=False, indent=2)
    for attempt in range(3):
        try:
            with open(AVATARS_META, 'w', encoding='utf-8') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            # 验证
            with open(AVATARS_META, 'r', encoding='utf-8') as f:
                if len(json.load(f)) == len(data):
                    return
        except Exception as e:
            print(f"[save_meta] attempt {attempt+1} fail: {e}")
            time.sleep(0.1)


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
        # 验证保存成功
        verify = load_meta()
        found = any(m.get("name") == name for m in verify)
        if found:
            print(f"[删除] [WARN] 验证失败：meta.json中仍存在「{name}」, 强制重写")
            save_meta(new_meta)
        else:
            print(f"[删除] [OK] 验证通过，剩余 {len(verify)} 个数字人")
        return True, f"已删除「{name}」"
    return False, "未找到该数字人"


def render_gallery(del_trigger_id="av-del-input", preview_trigger_id="av-prev-trigger"):
    """
    渲染数字人卡片 HTML。
    点击卡片主体触发预览，点击🗑按钮触发删除确认。
    """
    meta = load_meta()
    if not meta:
        return (
            '<div style="text-align:center;padding:56px 20px;color:#94a3b8;'
            'background:linear-gradient(135deg,#f8fafc,#f1f5f9);border-radius:16px;'
            'border:2px dashed #e2e8f0;">'
            '<div style="font-size:52px;margin-bottom:16px;filter:grayscale(.3);">🎭</div>'
            '<div style="font-size:14px;font-weight:700;color:#64748b;">暂无数字人</div>'
            '<div style="font-size:12px;margin-top:6px;color:#94a3b8;">在左侧上传视频并保存即可添加</div>'
            '</div>'
        )

    cards = ""
    for idx, m in enumerate(meta):
        name  = m.get("name", "未命名")
        path  = m.get("path", "")
        t     = m.get("time", "")
        exist = os.path.exists(path) if path else False
        dot   = "#22c55e" if exist else "#ef4444"
        status_text = "可用" if exist else "文件丢失"
        sz    = ""
        if exist:
            try:
                sz = f" · {os.path.getsize(path)/1048576:.1f}MB"
            except Exception:
                pass
        # JS：使用自定义删除对话框
        name_escaped = name.replace('\\', '\\\\').replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
        js_del = f"event.stopPropagation();window._zdaiTriggerDel('{del_trigger_id}','{name_escaped}','avatar');"
        js_preview = f"window._zdaiTriggerPreview('{preview_trigger_id}','{name_escaped}');"
        
        # 交替背景色
        bg = "#fff" if idx % 2 == 0 else "#fafbfc"
        
        cards += f"""
<div onclick="{js_preview}" style="display:flex;align-items:center;gap:14px;
  background:{bg};border:1.5px solid #e5e7eb;border-radius:14px;
  padding:12px 16px;margin-bottom:8px;cursor:pointer;
  box-shadow:0 1px 4px rgba(0,0,0,.03);
  transition:all .2s ease;"
  onmouseover="this.style.borderColor='#a5b4fc';this.style.boxShadow='0 4px 12px rgba(99,102,241,.1)'"
  onmouseout="this.style.borderColor='#e5e7eb';this.style.boxShadow='0 1px 4px rgba(0,0,0,.03)'">
  <div style="width:46px;height:46px;border-radius:12px;flex-shrink:0;
    background:linear-gradient(135deg,#6366f1,#8b5cf6);
    display:flex;align-items:center;justify-content:center;font-size:22px;
    box-shadow:0 2px 8px rgba(99,102,241,.25);">🎭</div>
  <div style="flex:1;min-width:0;">
    <div style="font-size:14px;font-weight:700;color:#0f172a;
      overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
      margin-bottom:3px;">{name}</div>
    <div style="font-size:11px;color:#94a3b8;display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
      <span style="display:inline-flex;align-items:center;gap:3px;">
        <span style="width:6px;height:6px;border-radius:50%;background:{dot};display:inline-block;"></span>
        <span style="color:{dot};font-weight:600;">{status_text}</span>
      </span>
      <span style="color:#cbd5e1;">|</span>
      <span>{os.path.basename(path) if path else "未知"}{sz}</span>
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
    header = (
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'margin-bottom:10px;padding:0 2px;">'
        f'<span style="font-size:12px;color:#64748b;font-weight:600;">共 {count} 个数字人</span>'
        f'<span style="font-size:11px;color:#94a3b8;">点击卡片预览 · 点击 🗑 删除</span>'
        f'</div>'
    )
    return f'{header}<div style="max-height:420px;overflow-y:auto;padding-right:2px;">{cards}</div>'