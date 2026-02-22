# -*- coding: utf-8 -*-
# lib_voice.py — 音色库管理（基于 MetaStore）

from lib_meta_store import MetaStore


class _VoiceStore(MetaStore):
    store_dir_name    = "voices"
    item_label        = "音色"
    upload_label      = "音频"
    default_ext       = ".wav"
    empty_icon        = "🎙"
    card_icon         = "🎙"
    card_gradient     = "linear-gradient(135deg,#0ea5e9,#0284c7)"
    card_shadow       = "rgba(14,165,233,.25)"
    card_hover_border = "#7dd3fc"
    card_hover_shadow = "rgba(14,165,233,.1)"
    del_type          = "voice"


_store = _VoiceStore()

# ── 向后兼容的模块级函数 ──
load_meta      = _store.load_meta
save_meta      = _store.save_meta
get_choices    = _store.get_choices
get_path       = _store.get_path
add_voice      = _store.add_item
del_voice      = _store.del_item
render_gallery = _store.render_gallery
