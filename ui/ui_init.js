
() => {
    /* ── 1. 禁用 SharedArrayBuffer 让 Gradio 自动降级到服务端处理 ── */
    try {
        Object.defineProperty(window,'SharedArrayBuffer',{get:()=>undefined,configurable:true});

        // 静默处理 FFmpeg 加载错误，不阻止请求但捕获错误
        window.addEventListener('unhandledrejection', function(event) {
            if (event.reason && event.reason.message &&
                (event.reason.message.includes('ffmpeg') ||
                 event.reason.message.includes('SharedArrayBuffer'))) {
                console.log('[织梦AI] FFmpeg WASM 已禁用，使用服务端处理');
                event.preventDefault(); // 阻止错误显示
            }
        });
    } catch(_){}

    /* ── 2. 隐藏 Gradio 页脚和无关按钮 ── */
    const _rmSel = [
        'footer','.footer','.built-with','#footer','div[class*="footer"]',
        '.show-api','.api-docs','a[href*="gradio.app"]','a[href*="huggingface"]',
        'button[aria-label="Settings"]','.hamburger-menu','span.version'
    ].join(',');
    const _rm = () => document.querySelectorAll(_rmSel).forEach(e => {
        e.style.cssText = 'display:none!important'; try { e.remove(); } catch(_){}
    });
    _rm();
    new MutationObserver(_rm).observe(document.documentElement, {childList:true, subtree:true});

    /* ── 2.5. 添加顶部标题栏（带版本号）── */
    setTimeout(() => {
        const container = document.querySelector('.gradio-container');
        if (container && !document.querySelector('.app-header')) {
            const header = document.createElement('div');
            header.className = 'app-header';
            header.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
                    <h1 style="margin: 0;">IP打造智能体</h1>
                    <span style="font-size: 14px; font-weight: 600; color: rgba(255,255,255,0.8); 
                                 background: rgba(255,255,255,0.15); padding: 6px 16px; 
                                 border-radius: 20px; backdrop-filter: blur(10px);">
                        v{{APP_VERSION}} (Build {{APP_BUILD}})
                    </span>
                </div>
            `;
            container.insertBefore(header, container.firstChild);
        }
    }, 100);

    /* ── 2.8. 立即定义关闭/最小化逻辑（必须在对话框HTML之前）── */
    window._zm = {
        show() {
            console.log('[织梦AI] _zm.show() 被调用');
            console.log('[织梦AI] 当前 window._zm 对象:', window._zm);
            const dialog = document.getElementById('zdai-cm');
            console.log('[织梦AI] 查找对话框元素 #zdai-cm:', dialog);
            if (dialog) {
                dialog.style.display = 'flex';
                console.log('[织梦AI] ✓ 关闭对话框已显示');
            } else {
                console.error('[织梦AI] ✗ 错误：关闭对话框元素不存在！');
                console.log('[织梦AI] DOM 状态:', document.readyState);
                console.log('[织梦AI] body 子元素数量:', document.body ? document.body.children.length : 'body不存在');
                // 如果对话框不存在，使用浏览器原生确认框
                if (confirm('确定要关闭程序吗？\n\n点击"确定"退出，点击"取消"返回')) {
                    this.exit();
                }
            }
        },
        hide() { 
            console.log('[织梦AI] _zm.hide() 被调用');
            const dialog = document.getElementById('zdai-cm');
            if (dialog) {
                dialog.style.display = 'none';
            }
        },
        minimize() {
            console.log('[织梦AI] _zm.minimize() 被调用');
            this.hide();
            setTimeout(() => {
                const api = window.pywebview?.api;
                if (api && typeof api.minimize_to_tray === 'function') {
                    Promise.resolve(api.minimize_to_tray())
                        .then(() => console.log('[织梦AI] 最小化完成'))
                        .catch(e => console.error('[织梦AI] 最小化失败:', e));
                } else {
                    console.warn('[织梦AI] pywebview.api 不可用，等待重试...');
                    setTimeout(() => {
                        if (window.pywebview?.api?.minimize_to_tray)
                            window.pywebview.api.minimize_to_tray();
                    }, 1000);
                }
            }, 200);
        },
        exit() {
            console.log('[织梦AI] _zm.exit() 被调用');
            this.hide();
            document.body.insertAdjacentHTML('beforeend',
                '<div style="position:fixed;inset:0;background:rgba(15,23,42,.95);z-index:999999;' +
                'display:flex;align-items:center;justify-content:center;flex-direction:column;gap:12px;' +
                'color:#fff;font-family:Microsoft YaHei,sans-serif;">' +
                '<div style="font-size:32px;">🌙</div>' +
                '<div style="font-size:16px;font-weight:700;">正在退出织梦AI...</div>' +
                '<div style="font-size:12px;color:#64748b;">正在保存数据并关闭服务</div></div>');
            setTimeout(() => {
                const api = window.pywebview?.api;
                if (api && typeof api.close_app === 'function') {
                    Promise.resolve(api.close_app())
                        .then(() => console.log('[织梦AI] 退出完成'))
                        .catch(e => console.error('[织梦AI] 退出失败:', e));
                } else {
                    console.warn('[织梦AI] pywebview.api.close_app 不可用');
                }
            }, 500);
        }
    };
    
    console.log('[织梦AI] window._zm 对象已初始化:', window._zm);
    
    // 测试：5秒后检查_zm对象是否还存在
    setTimeout(() => {
        console.log('[织梦AI] 5秒后检查 window._zm:', window._zm);
    }, 5000);

    /* ── 3. 关闭确认对话框 ── */
    document.body.insertAdjacentHTML('beforeend', `
      <div id="zdai-cm" style="display:none;position:fixed;inset:0;z-index:99999;align-items:center;justify-content:center;">
        <div style="position:absolute;inset:0;background:rgba(15,23,42,.6);backdrop-filter:blur(6px)" onclick="window._zm.hide()"></div>
        <div style="position:relative;background:#fff;border-radius:20px;padding:36px 32px 28px;width:380px;text-align:center;box-shadow:0 24px 64px rgba(0,0,0,.22)">
          <div style="width:56px;height:56px;border-radius:14px;background:linear-gradient(135deg,#6366f1,#8b5cf6);display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:26px;">🖥</div>
          <div style="font-size:18px;font-weight:800;color:#0f172a;margin-bottom:8px">关闭程序</div>
          <div style="font-size:13px;color:#64748b;margin-bottom:24px;line-height:1.7">最小化到通知区域后程序继续运行，<br>不会中断正在进行的任务。</div>
          <div style="display:flex;gap:10px">
            <button onclick="window._zm.minimize()" style="flex:1;padding:12px;border-radius:10px;border:1.5px solid #e2e8f0;background:#f8fafc;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;color:#374151;transition:all .15s">⊟ 最小化到通知区域</button>
            <button onclick="window._zm.exit()" style="flex:1;padding:12px;border-radius:10px;border:none;background:linear-gradient(135deg,#ef4444,#dc2626);color:#fff;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;transition:all .15s">✕ 退出程序</button>
          </div>
        </div>
      </div>

    `);

    /* ── 4. 进度浮层（视频合成期间显示生成进度）── */
    document.body.insertAdjacentHTML('beforeend', `
      <div id="zdai-prog" style="
          display:none;position:fixed;
          bottom:20px;right:20px;z-index:8900;
          background:linear-gradient(135deg,#1e293b,#0f172a);
          border:1.5px solid #6366f1;border-radius:14px;
          padding:14px 18px;min-width:260px;
          box-shadow:0 8px 32px rgba(0,0,0,.4);
          font-family:'Microsoft YaHei',system-ui,sans-serif;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
          <div style="width:8px;height:8px;border-radius:50%;background:#6366f1;
              animation:zdai-pulse 1.2s infinite;flex-shrink:0;"></div>
          <span id="zdai-prog-stage" style="font-size:12px;font-weight:700;color:#e2e8f0;">正在处理</span>
          <span id="zdai-prog-pct" style="font-size:12px;color:#6366f1;font-weight:700;margin-left:auto;">0%</span>
        </div>
        <div style="background:rgba(99,102,241,.15);border-radius:6px;height:6px;overflow:hidden;">
          <div id="zdai-prog-bar" style="height:100%;width:0%;border-radius:6px;
              background:linear-gradient(90deg,#6366f1,#8b5cf6);
              transition:width .4s ease;"></div>
        </div>
        <div id="zdai-prog-detail" style="font-size:11px;color:#64748b;margin-top:6px;"></div>
      </div>
      <style>
        @keyframes zdai-pulse {
          0%,100%{opacity:1;transform:scale(1)}
          50%{opacity:.5;transform:scale(.8)}
        }
      </style>`);

    window._zdaiSetProg = function(pct, stage, detail) {
        var el = document.getElementById('zdai-prog');
        if (!el) return;
        if (pct === null) { el.style.display = 'none'; return; }
        el.style.display = 'block';
        var bar  = document.getElementById('zdai-prog-bar');
        var pctEl= document.getElementById('zdai-prog-pct');
        var stEl = document.getElementById('zdai-prog-stage');
        var dtEl = document.getElementById('zdai-prog-detail');
        if (bar)   bar.style.width    = pct + '%';
        if (pctEl) pctEl.textContent  = pct + '%';
        if (stEl)  stEl.textContent   = stage || '处理中';
        if (dtEl)  dtEl.textContent   = detail || '';
    };

    /* ── 5. 系统通知 ── */
    window._zdaiNotify = (t, b) => {
        try { if (window.pywebview?.api) window.pywebview.api.send_notification(t, b); } catch(_){}
    };

    /* ── 6. 删除确认对话框（自定义UI）── */
    document.body.insertAdjacentHTML('beforeend', `
      <div id="zdai-del-modal" style="display:none;position:fixed;inset:0;z-index:99998;align-items:center;justify-content:center;">
        <div style="position:absolute;inset:0;background:rgba(15,23,42,.7);backdrop-filter:blur(8px)" onclick="window._zdaiDelModal.hide()"></div>
        <div style="position:relative;background:#fff;border-radius:20px;padding:32px 28px 24px;width:420px;text-align:center;box-shadow:0 24px 64px rgba(0,0,0,.25);animation:zdai-modal-in .2s ease-out">
          <div style="width:64px;height:64px;border-radius:16px;background:linear-gradient(135deg,#ef4444,#dc2626);display:flex;align-items:center;justify-content:center;margin:0 auto 18px;font-size:32px;box-shadow:0 8px 24px rgba(239,68,68,.3)">🗑</div>
          <div style="font-size:20px;font-weight:800;color:#0f172a;margin-bottom:10px" id="zdai-del-title">确认删除</div>
          <div style="font-size:14px;color:#64748b;margin-bottom:8px;line-height:1.8" id="zdai-del-msg">确定要删除此项吗？</div>
          <div style="background:#fef2f2;border:1.5px solid #fecaca;border-radius:12px;padding:12px 14px;margin-bottom:24px">
            <div style="font-size:13px;font-weight:700;color:#dc2626;margin-bottom:4px">⚠️ 警告</div>
            <div style="font-size:12px;color:#991b1b;line-height:1.6">删除后无法恢复，文件将被永久删除！</div>
          </div>
          <div style="display:flex;gap:12px">
            <button onclick="window._zdaiDelModal.hide()" style="flex:1;padding:14px;border-radius:12px;border:1.5px solid #e2e8f0;background:#f8fafc;font-size:14px;font-weight:700;cursor:pointer;font-family:inherit;color:#475569;transition:all .15s">取消</button>
            <button onclick="window._zdaiDelModal.confirm()" style="flex:1;padding:14px;border-radius:12px;border:none;background:linear-gradient(135deg,#ef4444,#dc2626);color:#fff;font-size:14px;font-weight:700;cursor:pointer;font-family:inherit;transition:all .15s;box-shadow:0 4px 12px rgba(239,68,68,.3)">确认删除</button>
          </div>
        </div>
      </div>
      <style>
        @keyframes zdai-modal-in {
          from { opacity:0; transform:scale(.95) translateY(-10px); }
          to { opacity:1; transform:scale(1) translateY(0); }
        }
        #zdai-del-modal button:hover {
          transform:translateY(-1px);
        }
      </style>
    `);

    window._zdaiDelModal = {
        _callback: null,
        show(title, msg, callback) {
            document.getElementById('zdai-del-title').textContent = title || '确认删除';
            document.getElementById('zdai-del-msg').textContent = msg || '确定要删除此项吗？';
            document.getElementById('zdai-del-modal').style.display = 'flex';
            this._callback = callback;
        },
        hide() {
            document.getElementById('zdai-del-modal').style.display = 'none';
            this._callback = null;
        },
        confirm() {
            if (this._callback) this._callback();
            this.hide();
        }
    };

    /* ── 7. 删除触发辅助函数（数字人/音色库删除按钮用）── */
    window._zdaiTriggerDel = function(elemId, name, type) {
        var typeText = type === 'avatar' ? '数字人' : '音色';
        window._zdaiDelModal.show(
            '删除' + typeText,
            '确定要删除' + typeText + '「' + name + '」吗？',
            function() {
                var tryCount = 0;
                var maxTries = 15;
                
                function tryTrigger() {
                    tryCount++;
                    var wrap = document.getElementById(elemId);
                    
                    if (!wrap) { 
                        if (tryCount < maxTries) {
                            setTimeout(tryTrigger, 200);
                            return;
                        }
                        console.error('[zdai] 找不到桥接元素:', elemId);
                        return;
                    }
                    
                    /* 临时恢复可交互性以便Gradio接收事件 */
                    var origStyle = wrap.style.cssText;
                    wrap.style.cssText = 'position:fixed;left:-9999px;opacity:0.01;pointer-events:auto;width:auto;height:auto;overflow:visible;z-index:-1;';
                    
                    var el = wrap.querySelector('textarea') || wrap.querySelector('input[type="text"]') || wrap.querySelector('input');
                    if (!el) { 
                        if (tryCount < maxTries) {
                            wrap.style.cssText = origStyle;
                            setTimeout(tryTrigger, 200);
                            return;
                        }
                        wrap.style.cssText = origStyle;
                        console.error('[zdai] 找不到 textarea/input in', elemId);
                        return; 
                    }
                    
                    /* 设置值并触发事件 */
                    try {
                        /* 先用带时间戳的唯一值确保change事件一定触发 */
                        var uniqueName = name;
                        
                        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                            window.HTMLTextAreaElement ? window.HTMLTextAreaElement.prototype : HTMLInputElement.prototype, 'value'
                        );
                        if (!nativeInputValueSetter) {
                            nativeInputValueSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
                        }
                        
                        if (nativeInputValueSetter && nativeInputValueSetter.set) {
                            nativeInputValueSetter.set.call(el, '');
                            el.dispatchEvent(new Event('input', {bubbles:true}));
                            
                            setTimeout(function() {
                                nativeInputValueSetter.set.call(el, uniqueName);
                                el.dispatchEvent(new Event('input',  {bubbles:true, cancelable:true}));
                                el.dispatchEvent(new Event('change', {bubbles:true, cancelable:true}));
                                console.log('[zdai] 删除触发成功 elemId=' + elemId + ' name=' + uniqueName);
                                
                                setTimeout(function() { wrap.style.cssText = origStyle; }, 500);
                            }, 50);
                        } else {
                            el.value = '';
                            el.dispatchEvent(new Event('input', {bubbles:true}));
                            setTimeout(function() {
                                el.value = uniqueName;
                                el.dispatchEvent(new Event('input',  {bubbles:true}));
                                el.dispatchEvent(new Event('change', {bubbles:true}));
                                setTimeout(function() { wrap.style.cssText = origStyle; }, 500);
                            }, 50);
                        }
                    } catch(e) { 
                        console.error('[zdai] 触发失败:', e);
                        el.value = name;
                        el.dispatchEvent(new Event('input',  {bubbles:true}));
                        el.dispatchEvent(new Event('change', {bubbles:true}));
                        setTimeout(function() { wrap.style.cssText = origStyle; }, 500);
                    }
                }
                
                tryTrigger();
            }
        );
    };

    /* ── 9b. 预览触发辅助函数（数字人/音色库卡片点击用）── */
    window._zdaiTriggerPreview = function(elemId, name) {
        var wrap = document.getElementById(elemId);
        if (!wrap) { console.warn('[zdai] 找不到预览桥接元素:', elemId); return; }
        
        var origStyle = wrap.style.cssText;
        wrap.style.cssText = 'position:fixed;left:-9999px;opacity:0.01;pointer-events:auto;width:auto;height:auto;overflow:visible;z-index:-1;';
        
        var el = wrap.querySelector('textarea') || wrap.querySelector('input[type="text"]') || wrap.querySelector('input');
        if (!el) { wrap.style.cssText = origStyle; return; }
        
        try {
            var setter = Object.getOwnPropertyDescriptor(
                el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype, 'value'
            );
            if (setter && setter.set) {
                setter.set.call(el, '');
                el.dispatchEvent(new Event('input', {bubbles:true}));
                setTimeout(function() {
                    setter.set.call(el, name);
                    el.dispatchEvent(new Event('input',  {bubbles:true}));
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                    setTimeout(function() { wrap.style.cssText = origStyle; }, 300);
                }, 30);
            } else {
                el.value = name;
                el.dispatchEvent(new Event('input',  {bubbles:true}));
                el.dispatchEvent(new Event('change', {bubbles:true}));
                setTimeout(function() { wrap.style.cssText = origStyle; }, 300);
            }
        } catch(e) {
            el.value = name;
            el.dispatchEvent(new Event('input',  {bubbles:true}));
            el.dispatchEvent(new Event('change', {bubbles:true}));
            setTimeout(function() { wrap.style.cssText = origStyle; }, 300);
        }
    };
    
    /* ── 9c. 工作台记录恢复/删除函数 ── */
    window._restoreWorkspaceRecord = function(index) {
        var input = document.querySelector('#workspace-record-to-restore textarea, #workspace-record-to-restore input');
        if (input) {
            input.value = String(index);
            input.dispatchEvent(new Event('input', {bubbles:true}));
            input.dispatchEvent(new Event('change', {bubbles:true}));
        }
    };
    
    /* ── 9d. 用户协议与隐私协议弹窗 ── */
    window._platformAiAgreementAccepted = false;
    
    window._showDouyinLoginAgreement = function(callback) {
        if (window._platformAiAgreementAccepted) {
            if (callback) callback(true);
            return;
        }
        
        var modal = document.getElementById('zdai-platform-ai-agreement-modal');
        if (!modal) {
            document.body.insertAdjacentHTML('beforeend', `
              <div id="zdai-platform-ai-agreement-modal" style="display:flex;position:fixed;inset:0;z-index:99999;align-items:center;justify-content:center;">
                <div style="position:absolute;inset:0;background:rgba(15,23,42,.85);backdrop-filter:blur(8px)"></div>
                <div style="position:relative;background:#fff;border-radius:20px;padding:32px 28px;width:90%;max-width:720px;max-height:85vh;display:flex;flex-direction:column;box-shadow:0 24px 64px rgba(0,0,0,.3)">
                  <div style="text-align:center;margin-bottom:20px;flex-shrink:0;">
                    <div style="width:56px;height:56px;border-radius:14px;background:linear-gradient(135deg,#6366f1,#8b5cf6);display:flex;align-items:center;justify-content:center;margin:0 auto 14px;font-size:28px;box-shadow:0 8px 24px rgba(99,102,241,.3)">📋</div>
                    <div style="font-size:20px;font-weight:800;color:#0f172a;margin-bottom:6px">用户协议与隐私协议</div>
                    <div style="font-size:12px;color:#64748b;">请阅读并同意以下条款后继续</div>
                  </div>
                  
                  <div style="display:flex;gap:6px;margin-bottom:14px;flex-shrink:0;" id="zdai-agreement-tabs">
                    <button id="zdai-tab-user" style="flex:1;padding:10px;border-radius:10px;border:none;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;transition:all .15s" onclick="document.getElementById('zdai-agreement-user').style.display='block';document.getElementById('zdai-agreement-privacy').style.display='none';this.style.background='linear-gradient(135deg,#6366f1,#8b5cf6)';this.style.color='#fff';document.getElementById('zdai-tab-privacy').style.background='#f1f5f9';document.getElementById('zdai-tab-privacy').style.color='#475569'">📄 用户协议</button>
                    <button id="zdai-tab-privacy" style="flex:1;padding:10px;border-radius:10px;border:none;background:#f1f5f9;color:#475569;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;transition:all .15s" onclick="document.getElementById('zdai-agreement-privacy').style.display='block';document.getElementById('zdai-agreement-user').style.display='none';this.style.background='linear-gradient(135deg,#6366f1,#8b5cf6)';this.style.color='#fff';document.getElementById('zdai-tab-user').style.background='#f1f5f9';document.getElementById('zdai-tab-user').style.color='#475569'">🔒 隐私协议</button>
                  </div>

                  <div id="zdai-agreement-user" style="background:#f8fafc;border:1.5px solid #e2e8f0;border-radius:14px;padding:20px 24px;margin-bottom:20px;overflow-y:auto;font-size:13px;line-height:1.9;color:#475569;flex:1;min-height:0;">
                    <h3 style="font-size:15px;font-weight:800;color:#0f172a;margin:0 0 16px 0;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">一、服务性质与责任边界</h3>
                    <p style="margin:0 0 12px 0;padding-left:0;">本软件（织梦AI）按"现状"方式提供，仅为技术辅助工具，不构成任何法律意见、合规意见、平台官方授权或收益保证。</p>
                    <p style="margin:0 0 16px 0;padding-left:0;">开发者不对以下事项作保证：平台审核通过、账号安全、AI生成内容准确性、第三方服务可用性、资源授权完整性。</p>

                    <h3 style="font-size:15px;font-weight:800;color:#0f172a;margin:20px 0 16px 0;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">二、用户承诺与义务</h3>
                    <ul style="margin:0 0 16px 0;padding-left:24px;">
                      <li>对上传、生成、发布的全部内容及素材拥有合法权利或已取得授权</li>
                      <li>不利用本软件实施违法违规、侵权、欺诈、虚假宣传等行为</li>
                      <li>不利用AI语音克隆、数字人功能冒充他人或制作虚假内容</li>
                      <li>自行负责账号安全、内容审核、授权核验及商业合规</li>
                    </ul>

                    <h3 style="font-size:15px;font-weight:800;color:#0f172a;margin:20px 0 16px 0;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">三、素材与资源授权</h3>
                    <p style="margin:0 0 16px 0;">除开发者明确标注为"已授权资源"外，本软件中出现的字体、音乐、模板等资源不视为开发者向用户授予任何知识产权许可。用户应自行核验授权范围。</p>

                    <h3 style="font-size:15px;font-weight:800;color:#0f172a;margin:20px 0 16px 0;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">四、AI功能合规</h3>
                    <p style="margin:0 0 16px 0;">AI语音克隆、数字人合成、深度合成等功能仅供合法用途。用户需遵守相关法律法规，在必要时对AI生成内容进行标识。</p>

                    <div style="background:#fef2f2;border:1.5px solid #fecaca;border-radius:10px;padding:14px 16px;margin-bottom:12px;">
                      <p style="margin:0 0 8px 0;font-weight:700;color:#dc2626;">⚠️ 重要提醒</p>
                      <ul style="margin:0;padding-left:20px;color:#991b1b;">
                        <li>请确保发布内容符合法律法规和平台规定</li>
                        <li>字体、音乐等素材需自行确认授权</li>
                        <li>自动发布功能存在平台风控风险</li>
                        <li>因违规使用导致的一切后果由用户承担</li>
                      </ul>
                    </div>
                    <p style="margin:0;font-size:12px;color:#64748b;text-align:center;padding-top:10px;border-top:1px solid #e2e8f0;">完整协议请查看程序目录下 user_agreement.md · 最后更新：2026年2月27日</p>
                  </div>

                  <div id="zdai-agreement-privacy" style="display:none;background:#f8fafc;border:1.5px solid #e2e8f0;border-radius:14px;padding:20px 24px;margin-bottom:20px;overflow-y:auto;font-size:13px;line-height:1.9;color:#475569;flex:1;min-height:0;">
                    <h3 style="font-size:15px;font-weight:800;color:#0f172a;margin:0 0 16px 0;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">一、信息收集</h3>
                    <p style="margin:0 0 12px 0;font-weight:600;">本地存储信息（仅保存在您的设备上）：</p>
                    <ul style="margin:0 0 16px 0;padding-left:24px;">
                      <li>软件配置与用户偏好设置</li>
                      <li>工作台记录与项目文件</li>
                      <li>字体、音频、模型缓存</li>
                      <li>浏览器用户数据（用于平台登录状态保持）</li>
                      <li>日志文件与错误记录</li>
                    </ul>
                    <p style="margin:0 0 12px 0;font-weight:600;">在线服务相关（仅在您主动使用时）：</p>
                    <ul style="margin:0 0 16px 0;padding-left:24px;">
                      <li>卡密验证：设备识别码、卡密信息</li>
                      <li>在线语音合成：文本内容</li>
                      <li>AI文案优化：文本内容</li>
                      <li>版本检查：软件版本号</li>
                    </ul>

                    <h3 style="font-size:15px;font-weight:800;color:#0f172a;margin:20px 0 16px 0;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">二、信息使用</h3>
                    <p style="margin:0 0 16px 0;">收集的信息仅用于：提供软件核心功能、验证授权状态、改善用户体验、故障排查与技术支持。</p>

                    <h3 style="font-size:15px;font-weight:800;color:#0f172a;margin:20px 0 16px 0;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">三、信息安全</h3>
                    <p style="margin:0 0 16px 0;">本软件不主动收集或上传您的个人隐私信息。在线传输采用加密通信。本地数据安全性取决于您的设备环境。</p>

                    <h3 style="font-size:15px;font-weight:800;color:#0f172a;margin:20px 0 16px 0;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">四、您的权利</h3>
                    <ul style="margin:0 0 16px 0;padding-left:24px;">
                      <li>访问权：可查看本地存储的所有数据</li>
                      <li>删除权：可随时删除本地缓存、日志等</li>
                      <li>选择权：可选择不使用在线功能</li>
                      <li>知情权：有权了解数据的收集和使用方式</li>
                    </ul>
                    <p style="margin:0;font-size:12px;color:#64748b;text-align:center;padding-top:10px;border-top:1px solid #e2e8f0;">完整隐私协议请查看程序目录下 privacy_policy.md · 最后更新：2026年2月27日</p>
                  </div>
                  
                  <div style="display:flex;gap:12px;flex-shrink:0;">
                    <button id="zdai-platform-ai-agreement-cancel" style="flex:1;padding:14px;border-radius:12px;border:1.5px solid #e2e8f0;background:#f8fafc;font-size:14px;font-weight:700;cursor:pointer;font-family:inherit;color:#475569;transition:all .15s">取消</button>
                    <button id="zdai-platform-ai-agreement-accept" style="flex:2;padding:14px;border-radius:12px;border:none;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;font-size:14px;font-weight:700;cursor:pointer;font-family:inherit;transition:all .15s;box-shadow:0 4px 12px rgba(99,102,241,.3)">我已阅读并同意</button>
                  </div>
                </div>
              </div>
            `);
            modal = document.getElementById('zdai-platform-ai-agreement-modal');
        } else {
            modal.style.display = 'flex';
        }
        
        document.getElementById('zdai-platform-ai-agreement-cancel').onclick = function() {
            modal.style.display = 'none';
            if (callback) callback(false);
        };
        
        document.getElementById('zdai-platform-ai-agreement-accept').onclick = function() {
            window._platformAiAgreementAccepted = true; window._douyinAgreementAccepted = true;
            modal.style.display = 'none';
            if (callback) callback(true);
        };
    };
    
    window._deleteWorkspaceRecord = function(index, name) {
        window._zdaiDelModal.show(
            '删除工作台记录',
            '确定要删除记录「' + name + '」吗？',
            function() {
                var input = document.querySelector('#workspace-record-to-delete textarea, #workspace-record-to-delete input');
                if (input) {
                    input.value = String(index);
                    input.dispatchEvent(new Event('input', {bubbles:true}));
                    input.dispatchEvent(new Event('change', {bubbles:true}));
                }
            }
        );
    };

    /* ── 10. 关闭/最小化逻辑已在前面定义 ── */
    // window._zm 对象已在文件开头定义，此处不再重复

    /* ── 11. 合成按钮互锁（任一合成按钮执行时禁止所有合成按钮）── */
    (function() {
        var _lockStart = 0;
        function checkBusy() {
            /* Gradio 在运行时会给按钮添加 .loading 类，或在容器上添加 .pending */
            var anyBusy = !!document.querySelector(
                'button.primary.loading, ' +
                '.pending button.primary, .generating button.primary'
            );
            
            /* 跟踪锁定时间，超过 120 秒强制解锁（防止出错后永久锁死）*/
            if (anyBusy) {
                if (!_lockStart) _lockStart = Date.now();
                if (Date.now() - _lockStart > 120000) {
                    anyBusy = false;
                    _lockStart = 0;
                }
            } else {
                _lockStart = 0;
            }
            
            /* 找到所有主按钮，排除工作台记录面板和关闭对话框的按钮 */
            var allBtns = document.querySelectorAll('button.primary:not(#workspace-record-panel button):not(#zdai-cm button):not(#zdai-del-modal button)');
            if (allBtns.length === 0) return;
            
            allBtns.forEach(function(b) {
                /* 跳过工作台记录面板内的按钮 */
                if (b.closest('#workspace-record-panel') || b.closest('#zdai-cm') || b.closest('#zdai-del-modal')) return;
                
                var isSelf = b.classList.contains('loading') || b.disabled;
                if (anyBusy && !isSelf) {
                    if (!b.dataset.zdLock) {
                        b.dataset.zdLock = '1';
                        b.dataset.zdOrigOpacity = b.style.opacity || '';
                        b.style.opacity = '0.45';
                        b.style.pointerEvents = 'none';
                        b.style.filter = 'grayscale(0.3)';
                    }
                } else if (b.dataset.zdLock) {
                    b.style.opacity = b.dataset.zdOrigOpacity || '';
                    b.style.pointerEvents = '';
                    b.style.filter = '';
                    delete b.dataset.zdLock;
                    delete b.dataset.zdOrigOpacity;
                }
            });
        }
        setInterval(checkBusy, 500);
        new MutationObserver(checkBusy).observe(document.documentElement, {
            childList: true, subtree: true, attributes: true,
            attributeFilter: ['class','disabled','style']
        });
    })();
    
    /* ── 12. 全局强制退出快捷键（Ctrl+Shift+Q）和F5刷新 ── */
    document.addEventListener('keydown', function(e) {
        // Ctrl+Shift+Q 强制退出
        if (e.ctrlKey && e.shiftKey && e.key === 'Q') {
            e.preventDefault();
            if (confirm('确定要强制退出程序吗？\n\n这将立即关闭所有进程。')) {
                try {
                    if (window.pywebview?.api?.close_app) {
                        window.pywebview.api.close_app();
                    }
                } catch(err) {
                    console.error('[EXIT] 强制退出失败:', err);
                }
            }
        }
        // F5 刷新页面
        if (e.key === 'F5') {
            e.preventDefault();
            window.location.reload();
        }
    });
    
    /* ── 13. 字体下拉框样式预览功能 ── */
    function applyFontPreview() {
        try {
            var fontDropdowns = [];
            document.querySelectorAll('label span').forEach(function(span) {
                if (span.textContent && span.textContent.indexOf('字体') !== -1) {
                    var block = span.closest('.block');
                    if (block) {
                        var dd = block.querySelector('select, .dropdown, [role="listbox"]');
                        if (dd) fontDropdowns.push(dd);
                    }
                }
            });
            fontDropdowns.forEach(function(dropdown) {
                var options = dropdown.querySelectorAll('option, [role="option"]');
                options.forEach(function(option) {
                    var fontName = option.textContent.trim();
                    if (fontName && !option.dataset.fontApplied) {
                        option.dataset.fontApplied = '1';
                        if (fontName === '系统字体') {
                            option.style.fontFamily = "'Microsoft YaHei', system-ui, sans-serif";
                        } else {
                            option.style.fontFamily = "'" + fontName + "', 'Microsoft YaHei', sans-serif";
                        }
                        option.style.fontSize = '16px';
                        option.style.padding = '8px 12px';
                    }
                });
            });
        } catch(_) {}
    }
    setTimeout(applyFontPreview, 2000);
    setTimeout(applyFontPreview, 5000);

    /* ── 15. 视频放大预览关闭按钮 ── */
    (function() {
        var CLOSE_BTN_ID = 'zdai-lightbox-close';

        function injectCloseBtn(container) {
            if (!container || container.querySelector('#' + CLOSE_BTN_ID)) return;
            var btn = document.createElement('button');
            btn.id = CLOSE_BTN_ID;
            btn.innerHTML = '✕ 关闭预览';
            btn.className = 'zdai-lightbox-close-btn';
            btn.onclick = function(e) {
                e.stopPropagation();
                // 尝试点击 Gradio 自带的关闭按钮
                var nativeClose = container.querySelector('button[aria-label="Close"], button[aria-label="close"], .close, .modalClose, [class*="close"]');
                if (nativeClose) {
                    nativeClose.click();
                    return;
                }
                // 兜底：按 Escape 键关闭
                document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', keyCode: 27, bubbles: true}));
                // 再兜底：直接隐藏
                setTimeout(function() {
                    if (container.parentNode) {
                        container.style.display = 'none';
                        // 尝试移除 body 上的 overflow:hidden
                        document.body.style.overflow = '';
                    }
                }, 100);
            };
            container.appendChild(btn);
        }

        // 监听 DOM 变化，检测 Gradio lightbox 弹出
        var observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(m) {
                m.addedNodes.forEach(function(node) {
                    if (node.nodeType !== 1) return;
                    // Gradio lightbox: 固定定位的全屏遮罩，包含 video 或 img
                    var el = node;
                    var isLightbox = false;

                    // 检查自身
                    if (el.matches && (
                        el.matches('[class*="modal"]') ||
                        el.matches('[class*="lightbox"]') ||
                        el.matches('[class*="preview"]')
                    )) {
                        var style = window.getComputedStyle(el);
                        if (style.position === 'fixed' && (el.querySelector('video') || el.querySelector('img'))) {
                            isLightbox = true;
                        }
                    }

                    // 检查是否是固定定位的全屏覆盖层（含 video）
                    if (!isLightbox && el.style) {
                        var cs = window.getComputedStyle(el);
                        if (cs.position === 'fixed' && cs.zIndex > 999 && (el.querySelector('video') || el.querySelector('img'))) {
                            isLightbox = true;
                        }
                    }

                    if (isLightbox) {
                        setTimeout(function() { injectCloseBtn(el); }, 50);
                    }
                });
            });

            // 也扫描已有的 Gradio modal（有些版本不是新增节点而是 display 切换）
            document.querySelectorAll('[class*="modal"]:not(#sub-settings-modal):not(#zdai-del-modal):not(#zdai-platform-ai-agreement-modal):not(#clear-confirm-overlay)').forEach(function(el) {
                var cs = window.getComputedStyle(el);
                if (cs.position === 'fixed' && cs.display !== 'none' && (el.querySelector('video') || el.querySelector('img'))) {
                    injectCloseBtn(el);
                }
            });
        });

        observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['style', 'class'] });
    })();

    /* ── 16. 字幕高级设置弹窗：点击外部区域（暗色遮罩）关闭 ── */
    (function() {
        document.addEventListener('click', function(e) {
            var modal = document.getElementById('sub-settings-modal');
            if (!modal) return;
            // 只处理可见状态的弹窗
            var cs = window.getComputedStyle(modal);
            if (cs.display === 'none' || cs.visibility === 'hidden') return;
            if (modal.offsetWidth === 0 && modal.offsetHeight === 0) return;
            // 检查点击的是否是打开按钮（避免打开后立即关闭）
            if (e.target.closest && e.target.closest('.sub-settings-btn')) return;
            // #sub-settings-modal 是全屏遮罩，其第一个子 div 是白色内容面板
            // 需要检查点击是否落在内容面板之外（即暗色遮罩区域）
            var panel = modal.querySelector(':scope > div');
            if (!panel) return;
            var rect = panel.getBoundingClientRect();
            var x = e.clientX, y = e.clientY;
            if (x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom) return;
            // 点击在内容面板外部（暗色遮罩上），触发取消按钮关闭弹窗
            var cancelWrapper = modal.querySelector('.sub-modal-close-btn');
            if (cancelWrapper) {
                var btn = cancelWrapper.querySelector('button') || cancelWrapper;
                btn.click();
            }
        });
    })();

    console.log('[织梦AI] 初始化完成 | Ctrl+Shift+Q 强制退出');

    /* ── 14. 下载按钮：弹出系统另存为对话框保存文件 ── */
    document.addEventListener('click', function(e) {
        var link = e.target.closest('a[download]');
        if (!link) return;
        var href = link.getAttribute('href') || link.href || '';
        if (!href || !href.includes('/file=')) return;

        e.preventDefault();
        e.stopPropagation();

        // 构造完整 URL
        var fullUrl = href.startsWith('http') ? href : window.location.origin + href;
        console.log('[织梦AI] 另存为下载:', fullUrl);

        // 调用 Python 端弹出另存为对话框
        if (window.pywebview && window.pywebview.api && window.pywebview.api.save_download_file) {
            window.pywebview.api.save_download_file(fullUrl);
        } else {
            // 兜底：直接用浏览器打开
            window.open(fullUrl);
        }
    }, true);
}
