# -*- coding: utf-8 -*-
# lib_avatar.py — 数字人库管理（基于 MetaStore）

from lib_meta_store import MetaStore


class _AvatarStore(MetaStore):
    store_dir_name   = "avatars"
    item_label       = "数字人"
    upload_label     = "视频"
    default_ext      = ".mp4"
    empty_icon       = "🎭"
    card_icon        = "🎭"
    card_gradient    = "linear-gradient(135deg,#6366f1,#8b5cf6)"
    card_shadow      = "rgba(99,102,241,.25)"
    card_hover_border = "#a5b4fc"
    card_hover_shadow = "rgba(99,102,241,.1)"
    del_type         = "avatar"


_store = _AvatarStore()

# ── 向后兼容的模块级函数 ──
load_meta      = _store.load_meta
save_meta      = _store.save_meta
get_choices    = _store.get_choices
get_path       = _store.get_path
add_avatar     = _store.add_item
del_avatar     = _store.del_item
render_gallery = _store.render_gallery
