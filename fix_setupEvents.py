import codecs

with codecs.open('dashboard/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

setup_events_full = """function setupEvents() {
    DOM.loginForm.addEventListener('submit', e => {
        e.preventDefault();
        let u = DOM.botUrlInput.value.trim().replace(/\\/$/, '');
        if (u && !u.startsWith('http://') && !u.startsWith('https://')) u = 'https://' + u;
        state.apiKey = DOM.apiKeyInput.value.trim();
        state.botUrl = u || '';
        testConnectionAndStart();
    });
    $$('.menu-item').forEach(i => i.addEventListener('click', e => { e.preventDefault(); switchTab(i.getAttribute('data-tab')); }));
    DOM.btnLogout.addEventListener('click', logout);
    DOM.btnRefresh.addEventListener('click', refreshData);
    DOM.btnTheme.addEventListener('click', toggleTheme);
    DOM.btnAutoRefresh.addEventListener('click', toggleAutoRefresh);
    $('btn-export').addEventListener('click', () => showModal($('exportModal')));
    
    if (DOM.statsProductSearch) {
        DOM.statsProductSearch.addEventListener('input', () => {
            renderStatsTable();
        });
    }

    $$('.sub-tab').forEach(t => t.addEventListener('click', () => {
        t.closest('.action-bar').querySelectorAll('.sub-tab').forEach(s => s.classList.remove('active'));
        t.closest('section').querySelectorAll('.sub-tab-content').forEach(c => c.classList.remove('active'));
        t.classList.add('active'); 
        let targetContent = document.querySelector(t.getAttribute('data-sub'));
        if (targetContent) targetContent.classList.add('active');
    }));

    $('btn-open-prod-modal').addEventListener('click', () => { DOM.addProdForm.reset(); DOM.prodId.value=''; if (DOM.prodDeliveryType) DOM.prodDeliveryType.value='stock'; showModal(DOM.prodModal); });
    const btnMassTranslate = $('btn-mass-translate');
    if (btnMassTranslate) btnMassTranslate.addEventListener('click', massTranslate);
    $('btn-open-promo-modal').addEventListener('click', () => {
        const sel = $('promo-products');
        sel.innerHTML = '';
        state.products.forEach(p => {
            const lbl = document.createElement('label');
            lbl.style.display = 'flex';
            lbl.style.alignItems = 'center';
            lbl.style.gap = '8px';
            lbl.style.cursor = 'pointer';
            lbl.style.margin = '0';
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.value = p.id;
            cb.className = 'promo-product-cb';
            lbl.appendChild(cb);
            lbl.appendChild(document.createTextNode(' ' + p.name));
            sel.appendChild(lbl);
        });
        showModal(DOM.promoModal);
    });
    $('btn-open-binance-modal').addEventListener('click', openBinanceModal);
    $$('.btn-close-modal').forEach(b => b.addEventListener('click', () => { [DOM.prodModal,DOM.stockModal,DOM.promoModal,DOM.tiersModal,DOM.orderDetailModal,DOM.viewStockModal,DOM.editProdModal,DOM.revenueModal,DOM.binanceModal,$('banModal'),$('finance-withdraw-modal'),$('finance-adjust-modal'), $('exportModal')].forEach(m => { if (m) hideModal(m); }); }));

    DOM.addProdForm.addEventListener('submit', handleAddProduct);
    DOM.addPromoForm.addEventListener('submit', handleAddPromo);
    DOM.settingsForm.addEventListener('submit', handleSaveSettings);
    DOM.cryptoSettingsForm.addEventListener('submit', handleSaveCryptoSettings);

    $$('.order-filter-btn').forEach(b => b.addEventListener('click', () => {
        $$('.order-filter-btn').forEach(x => x.classList.remove('active')); b.classList.add('active');
        state.orderFilter = b.getAttribute('data-status'); state.orderPage = 0; loadAllOrders();
    }));
    DOM.ordersPrev.addEventListener('click', () => { if (state.orderPage > 0) { state.orderPage--; loadAllOrders(); }});
    DOM.ordersNext.addEventListener('click', () => { if (state.orderPage < Math.ceil(state.orderTotal/20)-1) { state.orderPage++; loadAllOrders(); }});

    if (DOM.usersPrev) DOM.usersPrev.addEventListener('click', () => { if (state.usersPage > 0) { state.usersPage--; loadUsers(); }});
    if (DOM.usersNext) DOM.usersNext.addEventListener('click', () => { if (state.usersPage < Math.ceil(state.usersTotal/state.usersPerPage)-1) { state.usersPage++; loadUsers(); }});
    if (DOM.usersLimitSelector) {
        DOM.usersLimitSelector.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', () => {
                DOM.usersLimitSelector.querySelectorAll('button').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.usersPerPage = parseInt(btn.getAttribute('data-limit')) || 20;
                state.usersPage = 0;
                loadUsers();
            });
        });
    }
    if (DOM.usersSearch) {
        let searchTimeout;
        DOM.usersSearch.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                state.usersSearch = DOM.usersSearch.value.trim();
                state.usersPage = 0;
                loadUsers();
            }, 300);
        });
    }

    if (DOM.whPrev) DOM.whPrev.addEventListener('click', () => { if (state.whPage > 0) { state.whPage--; loadWalletHistory(); }});
    if (DOM.whNext) DOM.whNext.addEventListener('click', () => { if (state.whPage < Math.ceil(state.whTotal/20)-1) { state.whPage++; loadWalletHistory(); }});
    $$('.wh-filter-btn').forEach(b => b.addEventListener('click', () => {
        $$('.wh-filter-btn').forEach(x => x.classList.remove('active')); b.classList.add('active');
        state.whFilter = b.getAttribute('data-type'); state.whPage = 0; loadWalletHistory();
    }));

    DOM.stockTextarea.addEventListener('input', () => { const n = DOM.stockTextarea.value.split('\\n').filter(l=>l.trim()).length; DOM.stockLineCount.textContent = `${n} ${t('accounts_detected')}`; });
    DOM.btnAddStock.addEventListener('click', handleAddStock);
    DOM.stockFileInput.addEventListener('change', handleFileImport);
    DOM.btnSendBroadcast.addEventListener('click', handleBroadcast);
    DOM.broadcastBtnType.addEventListener('change', (e) => {
        const type = e.target.value;
        $('broadcast-buy-group').classList.toggle('hidden', type !== 'buy');
        $('broadcast-url-group').classList.toggle('hidden', type !== 'url');
    });
    $$('.lang-btn').forEach(b => b.addEventListener('click', () => setLang(b.getAttribute('data-lang'))));

    const btnTranslateAdd = $('btn-translate-add');
    const btnTranslateActAdd = $('btn-translate-act-add');
    const btnTranslateEdit = $('btn-translate-edit');
    const btnTranslateActEdit = $('btn-translate-act-edit');

    if (btnTranslateAdd) btnTranslateAdd.addEventListener('click', () => autoTranslate('add', false));
    if (btnTranslateActAdd) btnTranslateActAdd.addEventListener('click', () => autoTranslate('add', true));
    if (btnTranslateEdit) btnTranslateEdit.addEventListener('click', () => autoTranslate('edit', false));
    if (btnTranslateActEdit) btnTranslateActEdit.addEventListener('click', () => autoTranslate('edit', true));

    // Turbo Mode toggle listener
    const turboModeToggle = $('settings-turbo-mode');
    if (turboModeToggle) {
        turboModeToggle.addEventListener('change', (e) => {
            state.turboMode = e.target.checked;
            localStorage.setItem('vb_turbo', state.turboMode);
            document.body.classList.toggle('turbo-mode', state.turboMode);
        });
    }

    // Spotlight cursor follow effect
    document.addEventListener('mousemove', (e) => {
        if (!state.turboMode) return;
        const panels = document.querySelectorAll('.glass-panel');
        panels.forEach(el => {
            const rect = el.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            el.style.setProperty('--mouse-x', `${x}px`);
            el.style.setProperty('--mouse-y', `${y}px`);
        });
    });

    // Particle click burst
    document.addEventListener('click', (e) => {
        if (!state.turboMode) return;
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT' || e.target.closest('button') || e.target.closest('a')) return;
        createParticleBurst(e.clientX, e.clientY);
    });
}"""

import re
# We will find the start of setupEvents and the start of Particle Generator Utility
start_idx = content.find('function setupEvents() {')
end_idx = content.find('// ── Particle Generator Utility ──')

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + setup_events_full + '\n\n' + content[end_idx:]
    with codecs.open('dashboard/app.js', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Replaced successfully")
else:
    print(f"Could not find markers. Start: {start_idx}, End: {end_idx}")
