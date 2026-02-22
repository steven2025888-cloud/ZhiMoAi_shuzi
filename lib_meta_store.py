# -*- coding: utf-8 -*-
# lib_meta_store.py — 资源库通用基类（数字人 / 音色共用）

import os, re, json, shutil, time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class MetaStore:
    """
    通用资源库管理基类。
    子类只需提供差异化配置即可获得完整的 增 / 删 / 查 / 渲染 能力。
    """

    # ── 子类必须覆盖的配置 ──────────────────────────────
    store_dir_name: str = ""          # 存储目录名，如 "avatars" / "voices"
    item_label: str = "项目"           # 显示名，如 "数字人" / "音色"
    upload_label: str = "文件"         # 上传提示，如 "视频" / "音频"
    default_ext: str = ".mp4"         # 默认扩展名
    empty_icon: str = "📁"            # 空状态图标
    card_icon: str = "📁"             # 卡片图标
    card_gradient: str = "linear-gradient(135deg,#6366f1,#8b5cf6)"  # 卡片图标背景
    card_shadow: str = "rgba(99,102,241,.25)"                       # 卡片图标阴影
    card_hover_border: str = "#a5b4fc"                              # 悬停边框色
    card_hover_shadow: str = "rgba(99,102,241,.1)"                  # 悬停阴影色
    del_type: str = "item"            # JS 删除类型标识

    def __init__(self):
        self.store_dir = os.path.join(BASE_DIR, self.store_dir_name)
        self.meta_path = os.path.join(self.store_dir, "meta.json")
        os.makedirs(self.store_dir, exist_ok=True)

    # ── meta.json 读写 ─────────────────────────────────

    def load_meta(self) -> list:
        if os.path.exists(self.meta_path):
            try:
                with open(self.meta_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def save_meta(self, data: list):
        content = json.dumps(data, ensure_ascii=False, indent=2)
        for attempt in range(3):
            try:
                with open(self.meta_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                with open(self.meta_path, 'r', encoding='utf-8') as f:
                    if len(json.load(f)) == len(data):
                        return
            except Exception as e:
                print(f"[save_meta] attempt {attempt+1} fail: {e}")
                time.sleep(0.1)

    # ── 查询 ───────────────────────────────────────────

    def get_choices(self) -> list:
        items = [m for m in self.load_meta()
                 if m.get("path") and os.path.exists(m.get("path", ""))]
        if items:
            return [m["name"] for m in items]
        return [f"（暂无{self.item_label}，请先添加）"]

    def get_path(self, name: str):
        for m in self.load_meta():
            if m.get("name") == name:
                p = m.get("path", "")
                return p if os.path.exists(p) else None
        return None

    # ── 增删 ───────────────────────────────────────────

    def add_item(self, file_path, name: str) -> tuple:
        if not file_path or not os.path.exists(str(file_path)):
            return False, f"请先上传{self.upload_label}"
        name = (name or "").strip()
        if not name:
            return False, f"请输入{self.item_label}名称"
        for m in self.load_meta():
            if m.get("name") == name:
                return False, f"名称「{name}」已存在"
        ext = os.path.splitext(str(file_path))[1] or self.default_ext
        ts = int(time.time())
        safe = re.sub(r'[\\/:*?"<>|]', '_', name)
        dst = os.path.join(self.store_dir, f"{safe}_{ts}{ext}")
        try:
            shutil.copy2(str(file_path), dst)
        except Exception as e:
            return False, f"保存失败: {e}"
        meta = self.load_meta()
        meta.append({"name": name, "path": dst,
                      "time": time.strftime("%Y-%m-%d %H:%M")})
        self.save_meta(meta)
        return True, f"{self.item_label}「{name}」已保存"

    def del_item(self, name: str) -> tuple:
        if not name or name.startswith("（"):
            return False, f"请选择要删除的{self.item_label}"
        meta = self.load_meta()
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
            self.save_meta(new_meta)
            verify = self.load_meta()
            found = any(m.get("name") == name for m in verify)
            if found:
                print(f"[删除] [WARN] 验证失败：meta.json中仍存在「{name}」, 强制重写")
                self.save_meta(new_meta)
            else:
                print(f"[删除] [OK] 验证通过，剩余 {len(verify)} 个{self.item_label}")
            return True, f"已删除「{name}」"
        return False, f"未找到该{self.item_label}"

    # ── 卡片渲染 ───────────────────────────────────────

    def render_gallery(self, del_trigger_id: str = "del-input",
                       preview_trigger_id: str = "prev-trigger") -> str:
        meta = self.load_meta()
        if not meta:
            return (
                f'<div style="text-align:center;padding:56px 20px;color:#94a3b8;'
                f'background:linear-gradient(135deg,#f8fafc,#f1f5f9);border-radius:16px;'
                f'border:2px dashed #e2e8f0;">'
                f'<div style="font-size:52px;margin-bottom:16px;filter:grayscale(.3);">{self.empty_icon}</div>'
                f'<div style="font-size:14px;font-weight:700;color:#64748b;">暂无{self.item_label}</div>'
                f'<div style="font-size:12px;margin-top:6px;color:#94a3b8;">在左侧上传{self.upload_label}并保存即可添加</div>'
                f'</div>'
            )

        cards = ""
        for idx, m in enumerate(meta):
            name = m.get("name", "未命名")
            path = m.get("path", "")
            t = m.get("time", "")
            exist = os.path.exists(path) if path else False
            dot = "#22c55e" if exist else "#ef4444"
            status_text = "可用" if exist else "文件丢失"
            sz = ""
            if exist:
                try:
                    sz = f" · {os.path.getsize(path)/1048576:.1f}MB"
                except Exception:
                    pass
            name_escaped = (name.replace('\\', '\\\\').replace("'", "\\'")
                            .replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r'))
            js_del = (f"event.stopPropagation();"
                      f"window._zdaiTriggerDel('{del_trigger_id}','{name_escaped}','{self.del_type}');")
            js_preview = f"window._zdaiTriggerPreview('{preview_trigger_id}','{name_escaped}');"
            bg = "#fff" if idx % 2 == 0 else "#fafbfc"

            cards += f"""
<div onclick="{js_preview}" style="display:flex;align-items:center;gap:14px;
  background:{bg};border:1.5px solid #e5e7eb;border-radius:14px;
  padding:12px 16px;margin-bottom:8px;cursor:pointer;
  box-shadow:0 1px 4px rgba(0,0,0,.03);
  transition:all .2s ease;"
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
            f'<span style="font-size:12px;color:#64748b;font-weight:600;">共 {count} 个{self.item_label}</span>'
            f'<span style="font-size:11px;color:#94a3b8;">点击卡片预览 · 点击 🗑 删除</span>'
            f'</div>'
        )
        return f'{header}<div style="max-height:420px;overflow-y:auto;padding-right:2px;">{cards}</div>'
