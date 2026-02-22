# -*- coding: utf-8 -*-
"""
测试登录界面UI效果
"""
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import os

# 版本信息
CURRENT_VERSION = "1.0.9"
CURRENT_BUILD = 103

def create_login_window():
    root = tk.Tk()
    root.title("织梦AI大模型 - 专业版")
    root.resizable(False, False)
    
    # 设置窗口图标
    try:
        icon_path = "logo.ico"
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass

    # 居中
    w, h = 560, 750
    sx = (root.winfo_screenwidth() - w) // 2
    sy = (root.winfo_screenheight() - h) // 2
    root.geometry(f"{w}x{h}+{sx}+{sy}")

    # 创建渐变背景
    canvas = tk.Canvas(root, width=w, height=h, highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    
    # 绘制渐变背景
    for i in range(h):
        ratio = i / h
        r = int(30 + (99 - 30) * ratio)
        g = int(27 + (102 - 27) * ratio)
        b = int(75 + (241 - 75) * ratio)
        color = f'#{r:02x}{g:02x}{b:02x}'
        canvas.create_line(0, i, w, i, fill=color)
    
    # 装饰性几何图案
    canvas.create_oval(-80, -80, 120, 120, fill="", outline="#8b5cf6", width=2, dash=(10, 5))
    canvas.create_oval(-60, -60, 100, 100, fill="", outline="#a78bfa", width=1, dash=(5, 3))
    canvas.create_oval(w-120, h-120, w+80, h+80, fill="", outline="#8b5cf6", width=2, dash=(10, 5))
    canvas.create_oval(w-100, h-100, w+60, h+60, fill="", outline="#a78bfa", width=1, dash=(5, 3))
    
    # 顶部装饰线条
    for i in range(5):
        x1 = 80 + i * 100
        y1 = 50 + (i % 2) * 15
        x2 = x1 + 60
        y2 = y1
        canvas.create_line(x1, y1, x2, y2, fill="#c4b5fd", width=2, capstyle="round")

    # Logo区域
    logo_y = 110
    for r in range(70, 50, -5):
        canvas.create_oval(w//2-r, logo_y-r, w//2+r, logo_y+r,
                           fill="", outline="#c4b5fd", width=1, stipple="gray12")
    
    # 使用默认Logo
    canvas.create_oval(w//2-55, logo_y-55, w//2+55, logo_y+55, fill="#6366f1", outline="")
    canvas.create_oval(w//2-50, logo_y-50, w//2+50, logo_y+50, fill="#7c3aed", outline="")
    canvas.create_text(w//2, logo_y, text="✨", font=("Segoe UI Emoji", 48), fill="#ffffff")
    canvas.create_oval(w//2-58, logo_y-58, w//2+58, logo_y+58, outline="#ffffff", width=3)

    # 标题
    canvas.create_text(w//2, 210, text="织梦AI大模型", 
                       font=("Microsoft YaHei", 28, "bold"), fill="#ffffff")
    
    # 副标题
    canvas.create_rectangle(w//2-160, 245, w//2+160, 270,
                            fill="#5b21b6", outline="", stipple="gray25")
    canvas.create_text(w//2, 257, 
                       text="AI语音克隆 · 智能视频合成 · 专业级解决方案", 
                       font=("Microsoft YaHei", 10), fill="#e9d5ff")
    
    # 版本号（右下角）
    version_text = f"v{CURRENT_VERSION} (Build {CURRENT_BUILD})"
    canvas.create_text(w - 20, h - 15, text=version_text,
                       font=("Microsoft YaHei", 9), fill="#c4b5fd", anchor="e")

    # 卡片区域
    card_y = 300
    card_h = 380
    
    canvas.create_rectangle(44, card_y+6, w-44, card_y+card_h+6,
                            fill="#1e1b4b", outline="", stipple="gray25")
    canvas.create_rectangle(42, card_y+4, w-42, card_y+card_h+4,
                            fill="#312e81", outline="")
    canvas.create_rectangle(40, card_y, w-40, card_y+card_h,
                            fill="#ffffff", outline="")
    canvas.create_rectangle(40, card_y, w-40, card_y+4, fill="#6366f1", outline="")
    
    # 卡片内容
    card_frame = tk.Frame(root, bg="#ffffff")
    card_frame.place(x=70, y=card_y+25, width=w-140, height=card_h-50)

    # 标题
    tk.Label(card_frame, text="🔐 卡密登录", 
             font=("Microsoft YaHei", 16, "bold"),
             bg="#ffffff", fg="#1e293b").pack(pady=(0, 20))

    # 输入框
    tk.Label(card_frame, text="请输入您的卡密：",
             font=("Microsoft YaHei", 10),
             bg="#ffffff", fg="#64748b").pack(anchor="w")
    
    entry = tk.Entry(card_frame, font=("Microsoft YaHei", 11),
                     bg="#f8fafc", fg="#1e293b", relief="solid", bd=1)
    entry.pack(fill="x", pady=(5, 15), ipady=8)

    # 机器码
    tk.Label(card_frame, text="机器码：TEST-MACHINE-CODE-12345",
             font=("Consolas", 9), bg="#ffffff", fg="#94a3b8").pack(pady=(0, 15))

    # 协议勾选
    agreement_var = tk.BooleanVar(value=False)
    tk.Checkbutton(card_frame, text="我已阅读并同意《平台与AI功能使用协议》",
                   variable=agreement_var, font=("Microsoft YaHei", 9),
                   bg="#ffffff", fg="#64748b").pack(anchor="w", pady=(0, 15))

    # 登录按钮 - 渐变效果
    btn_container = tk.Frame(card_frame, bg="#ffffff", height=70)
    btn_container.pack(fill="x", pady=(15, 0))
    btn_container.pack_propagate(False)
    
    btn_canvas = tk.Canvas(btn_container, bg="#ffffff", highlightthickness=0, height=70)
    btn_canvas.pack(fill="both", expand=True)
    
    # 阴影
    btn_canvas.create_rectangle(8, 8, 412, 62, fill="#cbd5e1", outline="", tags="shadow")
    
    # 渐变背景
    btn_width = 400
    btn_height = 54
    btn_x = 10
    btn_y = 5
    
    for i in range(btn_width):
        ratio = i / btn_width
        r = int(99 + (139 - 99) * ratio)
        g = int(102 + (92 - 102) * ratio)
        b = int(241 + (246 - 241) * ratio)
        color = f'#{r:02x}{g:02x}{b:02x}'
        btn_canvas.create_line(btn_x + i, btn_y, btn_x + i, btn_y + btn_height,
                              fill=color, tags="btn_bg")
    
    # 按钮
    login_btn = tk.Button(
        btn_canvas,
        text="🚀  登录启动",
        font=("Microsoft YaHei", 14, "bold"),
        bg="#6366f1",
        fg="#ffffff",
        cursor="hand2",
        relief="flat",
        bd=0,
        command=lambda: print("登录按钮被点击")
    )
    btn_canvas.create_window(btn_width//2 + btn_x, btn_height//2 + btn_y,
                            window=login_btn, width=btn_width, height=btn_height)
    
    # 悬停效果
    def on_enter(e):
        btn_canvas.delete("btn_bg")
        for i in range(btn_width):
            ratio = i / btn_width
            r = int(79 + (107 - 79) * ratio)
            g = int(70 + (70 - 70) * ratio)
            b = int(229 + (230 - 229) * ratio)
            color = f'#{r:02x}{g:02x}{b:02x}'
            btn_canvas.create_line(btn_x + i, btn_y, btn_x + i, btn_y + btn_height,
                                  fill=color, tags="btn_bg")
        btn_canvas.tag_lower("btn_bg")
    
    def on_leave(e):
        btn_canvas.delete("btn_bg")
        for i in range(btn_width):
            ratio = i / btn_width
            r = int(99 + (139 - 99) * ratio)
            g = int(102 + (92 - 102) * ratio)
            b = int(241 + (246 - 241) * ratio)
            color = f'#{r:02x}{g:02x}{b:02x}'
            btn_canvas.create_line(btn_x + i, btn_y, btn_x + i, btn_y + btn_height,
                                  fill=color, tags="btn_bg")
        btn_canvas.tag_lower("btn_bg")
    
    login_btn.bind("<Enter>", on_enter)
    login_btn.bind("<Leave>", on_leave)

    root.mainloop()

if __name__ == "__main__":
    print("=" * 60)
    print("测试登录界面UI")
    print("=" * 60)
    print()
    print("功能：")
    print("  1. 渐变背景")
    print("  2. 渐变登录按钮")
    print("  3. 版本号显示（右下角）")
    print("  4. 鼠标悬停效果")
    print()
    print("关闭窗口即可退出测试")
    print("=" * 60)
    print()
    
    create_login_window()
