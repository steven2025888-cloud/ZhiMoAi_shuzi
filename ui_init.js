
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
    
    /* ── 9d. 抖音发布免责声明（登录时显示）── */
    window._platformAiAgreementAccepted = false;
    
    window._showDouyinLoginAgreement = function(callback) {
        // 如果已经同意过，直接执行回调
        if (window._platformAiAgreementAccepted) {
            if (callback) callback(true);
            return;
        }
        
        // 显示协议弹窗
        var modal = document.getElementById('zdai-platform-ai-agreement-modal');
        if (!modal) {
            // 创建弹窗
            document.body.insertAdjacentHTML('beforeend', `
              <div id="zdai-platform-ai-agreement-modal" style="display:flex;position:fixed;inset:0;z-index:99999;align-items:center;justify-content:center;">
                <div style="position:absolute;inset:0;background:rgba(15,23,42,.85);backdrop-filter:blur(8px)"></div>
                <div style="position:relative;background:#fff;border-radius:20px;padding:32px 28px;width:90%;max-width:680px;max-height:85vh;overflow-y:auto;box-shadow:0 24px 64px rgba(0,0,0,.3)">
                  <div style="text-align:center;margin-bottom:24px;">
                    <div style="width:64px;height:64px;border-radius:16px;background:linear-gradient(135deg,#f59e0b,#d97706);display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:32px;box-shadow:0 8px 24px rgba(245,158,11,.3)">⚠️</div>
                    <div style="font-size:22px;font-weight:800;color:#0f172a;margin-bottom:8px">平台与AI功能使用协议</div>
                    <div style="font-size:13px;color:#64748b;">首次登录前必须阅读并同意以下条款</div>
                  </div>
                  
                  <div style="background:#f8fafc;border:1.5px solid #e2e8f0;border-radius:14px;padding:20px 24px;margin-bottom:24px;max-height:400px;overflow-y:auto;font-size:13px;line-height:1.9;color:#475569;">
                    <h3 style="font-size:15px;font-weight:800;color:#0f172a;margin:0 0 16px 0;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">一、免责声明</h3>
                    
                    <p style="margin:0 0 12px 0;"><strong>1.1 服务性质</strong></p>
                    <p style="margin:0 0 16px 0;padding-left:16px;">本软件提供的平台发布与AI处理功能仅为技术工具，用于辅助用户在多个平台进行内容处理与发布。本软件不对发布内容的合法性、真实性、准确性承担任何责任。</p>
                    
                    <p style="margin:0 0 12px 0;"><strong>1.2 内容责任</strong></p>
                    <p style="margin:0 0 16px 0;padding-left:16px;">用户对其发布的所有内容（包括但不限于视频、文字、图片、音频等）承担全部法律责任。用户保证其发布的内容：</p>
                    <ul style="margin:0 0 16px 0;padding-left:36px;">
                      <li>不侵犯任何第三方的知识产权、肖像权、隐私权等合法权益</li>
                      <li>不包含违法、违规、淫秽、暴力、恐怖、诽谤等不良信息</li>
                      <li>符合国家法律法规及相关平台规则</li>
                      <li>不用于任何商业欺诈、虚假宣传等违法违规行为</li>
                    </ul>
                    
                    <p style="margin:0 0 12px 0;"><strong>1.3 账号安全</strong></p>
                    <p style="margin:0 0 16px 0;padding-left:16px;">用户需妥善保管自己的抖音账号信息。因用户账号泄露、被盗用等原因导致的任何损失，本软件不承担责任。</p>
                    
                    <p style="margin:0 0 12px 0;"><strong>1.4 平台规则</strong></p>
                    <p style="margin:0 0 16px 0;padding-left:16px;">抖音平台可能随时调整其服务条款、发布规则、审核标准等。因平台规则变化导致的发布失败、内容被删除、账号被封禁等情况，本软件不承担任何责任。</p>
                    
                    <p style="margin:0 0 12px 0;"><strong>1.5 技术限制</strong></p>
                    <p style="margin:0 0 16px 0;padding-left:16px;">本软件依赖第三方技术和服务，可能因技术故障、网络中断、平台更新等原因导致功能异常。本软件不保证服务的持续性、稳定性和准确性。</p>
                    
                    <h3 style="font-size:15px;font-weight:800;color:#0f172a;margin:24px 0 16px 0;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">二、用户协议</h3>
                    
                    <p style="margin:0 0 12px 0;"><strong>2.1 合法使用</strong></p>
                    <p style="margin:0 0 16px 0;padding-left:16px;">用户承诺仅将本软件用于合法目的，不得用于任何违法违规活动。</p>
                    
                    <p style="margin:0 0 12px 0;"><strong>2.2 自担风险</strong></p>
                    <p style="margin:0 0 16px 0;padding-left:16px;">用户理解并同意，使用本软件发布内容可能面临的风险（包括但不限于内容被删除、账号被封禁、法律纠纷等）由用户自行承担。</p>
                    
                    <p style="margin:0 0 12px 0;"><strong>2.3 数据隐私</strong></p>
                    <p style="margin:0 0 16px 0;padding-left:16px;">本软件会在本地保存用户的登录状态，用于保持登录便利性。本软件不会收集、上传或泄露用户的个人信息和账号数据。</p>
                    
                    <h3 style="font-size:15px;font-weight:800;color:#0f172a;margin:24px 0 16px 0;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">三、特别提示</h3>
                    
                    <div style="background:#fef2f2;border:1.5px solid #fecaca;border-radius:10px;padding:14px 16px;margin-bottom:16px;">
                      <p style="margin:0 0 8px 0;font-weight:700;color:#dc2626;">⚠️ 重要提醒</p>
                      <ul style="margin:0;padding-left:20px;color:#991b1b;">
                        <li>请确保发布内容符合法律法规和平台规定</li>
                        <li>请勿发布侵权、违规、不良信息</li>
                        <li>账号安全由用户自行负责</li>
                        <li>因违规使用导致的一切后果由用户承担</li>
                      </ul>
                    </div>
                    
                    <p style="margin:0;font-size:12px;color:#64748b;text-align:center;padding-top:12px;border-top:1px solid #e2e8f0;">
                      最后更新日期：2026年2月22日
                    </p>
                  </div>
                  
                  <div style="display:flex;gap:12px;">
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
        
        // 绑定按钮事件
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
        function checkBusy() {
            /* Gradio 在运行时会给按钮添加 .loading 类，或在容器上添加 .pending */
            var anyBusy = !!document.querySelector(
                'button.primary.loading, button.primary[disabled], ' +
                '.pending button.primary, .generating button.primary, ' +
                '.progress-bar:not([style*="display: none"]):not([style*="display:none"])'
            );
            /* 找到所有主按钮，排除工作台记录面板的按钮 */
            var allBtns = document.querySelectorAll('button.primary:not(#workspace-record-panel button)');
            if (allBtns.length === 0) return;
            
            allBtns.forEach(function(b) {
                /* 跳过工作台记录面板内的按钮 */
                if (b.closest('#workspace-record-panel')) return;
                
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

    console.log('[织梦AI] 初始化完成 | Ctrl+Shift+Q 强制退出');
}
