import codecs

with codecs.open('dashboard/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Restore missing init block
missing_init = """    $$('.sub-tab').forEach(t => t.addEventListener('click', () => {
        t.closest('.action-bar').querySelectorAll('.sub-tab').forEach(s => s.classList.remove('active'));
        t.closest('section').querySelectorAll('.sub-tab-content').forEach(c => c.classList.remove('active'));
        t.classList.add('active'); $(t.getAttribute('data-sub')).classList.add('active');
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

    DOM.addProdForm.addEventListener('submit', handleAddProduct);"""

content = content.replace("""    $$('.sub-tab').forEach(t => t.addEventListener('click', () => {
    DOM.addProdForm.addEventListener('submit', handleAddProduct);""", missing_init)

# 2. autoTranslate event listeners
translate_events_old = """    const btnTranslateAdd = $('btn-translate-add');
    if (btnTranslateAdd) btnTranslateAdd.addEventListener('click', () => autoTranslate('add'));
    
    const btnTranslateEdit = $('btn-translate-edit');
    if (btnTranslateEdit) btnTranslateEdit.addEventListener('click', () => autoTranslate('edit'));"""

translate_events_new = """    const btnTranslateAdd = $('btn-translate-add');
    const btnTranslateActAdd = $('btn-translate-act-add');
    const btnTranslateEdit = $('btn-translate-edit');
    const btnTranslateActEdit = $('btn-translate-act-edit');

    if (btnTranslateAdd) btnTranslateAdd.addEventListener('click', () => autoTranslate('add', false));
    if (btnTranslateActAdd) btnTranslateActAdd.addEventListener('click', () => autoTranslate('add', true));
    if (btnTranslateEdit) btnTranslateEdit.addEventListener('click', () => autoTranslate('edit', false));
    if (btnTranslateActEdit) btnTranslateActEdit.addEventListener('click', () => autoTranslate('edit', true));"""
content = content.replace(translate_events_old, translate_events_new)

# 3. autoTranslate function
auto_translate_old = """async function autoTranslate(type) {
    const btn = type === 'add' ? $('btn-translate-add') : $('btn-translate-edit');
    const sourceTextarea = type === 'add' ? DOM.prodDesc : $('edit-prod-desc');
    const targetFr = type === 'add' ? $('prod-desc-fr') : $('edit-prod-desc-fr');
    const targetAr = type === 'add' ? $('prod-desc-ar') : $('edit-prod-desc-ar');
    const targetZh = type === 'add' ? $('prod-desc-zh') : $('edit-prod-desc-zh');"""

auto_translate_new = """async function autoTranslate(type, isAct = false) {
    const btn = type === 'add' 
        ? (isAct ? $('btn-translate-act-add') : $('btn-translate-add')) 
        : (isAct ? $('btn-translate-act-edit') : $('btn-translate-edit'));
    const sourceTextarea = type === 'add' 
        ? (isAct ? $('prod-act-msg') : DOM.prodDesc) 
        : (isAct ? $('edit-prod-act-msg') : $('edit-prod-desc'));
    const targetFr = type === 'add' 
        ? (isAct ? $('prod-act-msg-fr') : $('prod-desc-fr')) 
        : (isAct ? $('edit-prod-act-msg-fr') : $('edit-prod-desc-fr'));
    const targetAr = type === 'add' 
        ? (isAct ? $('prod-act-msg-ar') : $('prod-desc-ar')) 
        : (isAct ? $('edit-prod-act-msg-ar') : $('edit-prod-desc-ar'));
    const targetZh = type === 'add' 
        ? (isAct ? $('prod-act-msg-zh') : $('prod-desc-zh')) 
        : (isAct ? $('edit-prod-act-msg-zh') : $('edit-prod-desc-zh'));"""
content = content.replace(auto_translate_old, auto_translate_new)

# 4. massTranslate function (filter)
mass_translate_old = """    const toTranslate = state.products.filter(p => {
        const hasEn = p.description && p.description.trim().length > 0;
        const missingTranslation = !p.description_fr || !p.description_ar || !p.description_zh;
        return hasEn && missingTranslation;
    });"""

mass_translate_new = """    const toTranslate = state.products.filter(p => {
        const hasEnDesc = p.description && p.description.trim().length > 0;
        const missingDescTrans = hasEnDesc && (!p.description_fr || !p.description_ar || !p.description_zh);
        
        const hasEnAct = p.activation_message && p.activation_message.trim().length > 0;
        const missingActTrans = hasEnAct && (!p.activation_message_fr || !p.activation_message_ar || !p.activation_message_zh);
        
        return missingDescTrans || missingActTrans;
    });"""
content = content.replace(mass_translate_old, mass_translate_new)

# 4b. massTranslate function (API calls)
mass_translate_api_old = """            // Call Gemini
            const res = await apiCall('/api/translate', 'POST', { text: p.description });
            
            // Build updates for the missing fields
            const updates = {};
            if (!p.description_fr && res.fr) updates.description_fr = res.fr;
            if (!p.description_ar && res.ar) updates.description_ar = res.ar;
            if (!p.description_zh && res.zh) updates.description_zh = res.zh;
            
            // Save to database
            if (Object.keys(updates).length > 0) {
                await apiCall(`/api/products/${p.id}`, 'PUT', updates);
                // Update local state so product won't be re-translated if cancelled and restarted
                if (updates.description_fr) p.description_fr = updates.description_fr;
                if (updates.description_ar) p.description_ar = updates.description_ar;
                if (updates.description_zh) p.description_zh = updates.description_zh;
                successCount++;
            }"""

mass_translate_api_new = """            // Build updates for the missing fields
            const updates = {};
            
            // Translate description
            if (p.description && (!p.description_fr || !p.description_ar || !p.description_zh)) {
                const res = await apiCall('/api/translate', 'POST', { text: p.description });
                if (!p.description_fr && res.fr) updates.description_fr = res.fr;
                if (!p.description_ar && res.ar) updates.description_ar = res.ar;
                if (!p.description_zh && res.zh) updates.description_zh = res.zh;
            }
            
            // Translate activation message
            if (p.activation_message && (!p.activation_message_fr || !p.activation_message_ar || !p.activation_message_zh)) {
                const resAct = await apiCall('/api/translate', 'POST', { text: p.activation_message });
                if (!p.activation_message_fr && resAct.fr) updates.activation_message_fr = resAct.fr;
                if (!p.activation_message_ar && resAct.ar) updates.activation_message_ar = resAct.ar;
                if (!p.activation_message_zh && resAct.zh) updates.activation_message_zh = resAct.zh;
            }
            
            // Save to database
            if (Object.keys(updates).length > 0) {
                await apiCall(`/api/products/${p.id}`, 'PUT', updates);
                // Update local state so product won't be re-translated if cancelled and restarted
                if (updates.description_fr) p.description_fr = updates.description_fr;
                if (updates.description_ar) p.description_ar = updates.description_ar;
                if (updates.description_zh) p.description_zh = updates.description_zh;
                if (updates.activation_message_fr) p.activation_message_fr = updates.activation_message_fr;
                if (updates.activation_message_ar) p.activation_message_ar = updates.activation_message_ar;
                if (updates.activation_message_zh) p.activation_message_zh = updates.activation_message_zh;
                successCount++;
            }"""
content = content.replace(mass_translate_api_old, mass_translate_api_new)

# 5. Populate Edit form
edit_form_pop_old = """    $('edit-prod-desc').value = p.description || '';
    if ($('edit-prod-desc-fr')) $('edit-prod-desc-fr').value = p.description_fr || '';
    if ($('edit-prod-desc-ar')) $('edit-prod-desc-ar').value = p.description_ar || '';
    if ($('edit-prod-desc-zh')) $('edit-prod-desc-zh').value = p.description_zh || '';"""

edit_form_pop_new = """    $('edit-prod-desc').value = p.description || '';
    if ($('edit-prod-desc-fr')) $('edit-prod-desc-fr').value = p.description_fr || '';
    if ($('edit-prod-desc-ar')) $('edit-prod-desc-ar').value = p.description_ar || '';
    if ($('edit-prod-desc-zh')) $('edit-prod-desc-zh').value = p.description_zh || '';
    if ($('edit-prod-act-msg')) $('edit-prod-act-msg').value = p.activation_message || '';
    if ($('edit-prod-act-msg-fr')) $('edit-prod-act-msg-fr').value = p.activation_message_fr || '';
    if ($('edit-prod-act-msg-ar')) $('edit-prod-act-msg-ar').value = p.activation_message_ar || '';
    if ($('edit-prod-act-msg-zh')) $('edit-prod-act-msg-zh').value = p.activation_message_zh || '';"""
content = content.replace(edit_form_pop_old, edit_form_pop_new)

# 6. Submit Edit form
edit_form_submit_old = """            description: $('edit-prod-desc').value.trim(),
            description_fr: $('edit-prod-desc-fr') ? $('edit-prod-desc-fr').value.trim() : '',
            description_ar: $('edit-prod-desc-ar') ? $('edit-prod-desc-ar').value.trim() : '',
            description_zh: $('edit-prod-desc-zh') ? $('edit-prod-desc-zh').value.trim() : '',
            image_url: $('edit-prod-image-url').value.trim(),"""

edit_form_submit_new = """            description: $('edit-prod-desc').value.trim(),
            description_fr: $('edit-prod-desc-fr') ? $('edit-prod-desc-fr').value.trim() : '',
            description_ar: $('edit-prod-desc-ar') ? $('edit-prod-desc-ar').value.trim() : '',
            description_zh: $('edit-prod-desc-zh') ? $('edit-prod-desc-zh').value.trim() : '',
            activation_message: $('edit-prod-act-msg') ? $('edit-prod-act-msg').value.trim() : '',
            activation_message_fr: $('edit-prod-act-msg-fr') ? $('edit-prod-act-msg-fr').value.trim() : '',
            activation_message_ar: $('edit-prod-act-msg-ar') ? $('edit-prod-act-msg-ar').value.trim() : '',
            activation_message_zh: $('edit-prod-act-msg-zh') ? $('edit-prod-act-msg-zh').value.trim() : '',
            image_url: $('edit-prod-image-url').value.trim(),"""
content = content.replace(edit_form_submit_old, edit_form_submit_new)

# 7. Submit Add form
add_form_submit_old = """            description_fr: $('prod-desc-fr') ? $('prod-desc-fr').value.trim() : '',
            description_ar: $('prod-desc-ar') ? $('prod-desc-ar').value.trim() : '',
            description_zh: $('prod-desc-zh') ? $('prod-desc-zh').value.trim() : '',
            delivery_type: $('prod-delivery-type').value"""

add_form_submit_new = """            description_fr: $('prod-desc-fr') ? $('prod-desc-fr').value.trim() : '',
            description_ar: $('prod-desc-ar') ? $('prod-desc-ar').value.trim() : '',
            description_zh: $('prod-desc-zh') ? $('prod-desc-zh').value.trim() : '',
            activation_message: $('prod-act-msg') ? $('prod-act-msg').value.trim() : '',
            activation_message_fr: $('prod-act-msg-fr') ? $('prod-act-msg-fr').value.trim() : '',
            activation_message_ar: $('prod-act-msg-ar') ? $('prod-act-msg-ar').value.trim() : '',
            activation_message_zh: $('prod-act-msg-zh') ? $('prod-act-msg-zh').value.trim() : '',
            delivery_type: $('prod-delivery-type').value"""
content = content.replace(add_form_submit_old, add_form_submit_new)

with codecs.open('dashboard/app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('app.js successfully updated via script.')
