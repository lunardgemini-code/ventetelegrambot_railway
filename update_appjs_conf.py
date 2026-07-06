import codecs

with codecs.open('dashboard/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update DOM definitions (not strictly necessary to define everything in DOM if we just use $ in the functions, but let's just use $ everywhere)
# Wait, let's just use $() directly in the code to avoid touching the giant DOM object.

# 2. Update autoTranslate
auto_trans_old = """async function autoTranslate(type, isAct = false) {
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

auto_trans_new = """async function autoTranslate(type, msgType = 'desc') {
    let btn, sourceTextarea, targetFr, targetAr, targetZh;
    
    if (type === 'add') {
        if (msgType === 'act') {
            btn = $('btn-translate-act-add'); sourceTextarea = $('prod-act-msg');
            targetFr = $('prod-act-msg-fr'); targetAr = $('prod-act-msg-ar'); targetZh = $('prod-act-msg-zh');
        } else if (msgType === 'conf') {
            btn = $('btn-translate-conf-add'); sourceTextarea = $('prod-conf-msg');
            targetFr = $('prod-conf-msg-fr'); targetAr = $('prod-conf-msg-ar'); targetZh = $('prod-conf-msg-zh');
        } else {
            btn = $('btn-translate-add'); sourceTextarea = DOM.prodDesc;
            targetFr = $('prod-desc-fr'); targetAr = $('prod-desc-ar'); targetZh = $('prod-desc-zh');
        }
    } else {
        if (msgType === 'act') {
            btn = $('btn-translate-act-edit'); sourceTextarea = $('edit-prod-act-msg');
            targetFr = $('edit-prod-act-msg-fr'); targetAr = $('edit-prod-act-msg-ar'); targetZh = $('edit-prod-act-msg-zh');
        } else if (msgType === 'conf') {
            btn = $('btn-translate-conf-edit'); sourceTextarea = $('edit-prod-conf-msg');
            targetFr = $('edit-prod-conf-msg-fr'); targetAr = $('edit-prod-conf-msg-ar'); targetZh = $('edit-prod-conf-msg-zh');
        } else {
            btn = $('btn-translate-edit'); sourceTextarea = $('edit-prod-desc');
            targetFr = $('edit-prod-desc-fr'); targetAr = $('edit-prod-desc-ar'); targetZh = $('edit-prod-desc-zh');
        }
    }"""
content = content.replace(auto_trans_old, auto_trans_new)

# 3. Update massTranslate filter
mass_filter_old = """    const toTranslate = state.products.filter(p => {
        const hasEnDesc = p.description && p.description.trim().length > 0;
        const missingDescTrans = hasEnDesc && (!p.description_fr || !p.description_ar || !p.description_zh);
        
        const hasEnAct = p.activation_message && p.activation_message.trim().length > 0;
        const missingActTrans = hasEnAct && (!p.activation_message_fr || !p.activation_message_ar || !p.activation_message_zh);
        
        return missingDescTrans || missingActTrans;
    });"""

mass_filter_new = """    const toTranslate = state.products.filter(p => {
        const hasEnDesc = p.description && p.description.trim().length > 0;
        const missingDescTrans = hasEnDesc && (!p.description_fr || !p.description_ar || !p.description_zh);
        
        const hasEnAct = p.activation_message && p.activation_message.trim().length > 0;
        const missingActTrans = hasEnAct && (!p.activation_message_fr || !p.activation_message_ar || !p.activation_message_zh);
        
        const hasEnConf = p.confirmation_message && p.confirmation_message.trim().length > 0;
        const missingConfTrans = hasEnConf && (!p.confirmation_message_fr || !p.confirmation_message_ar || !p.confirmation_message_zh);
        
        return missingDescTrans || missingActTrans || missingConfTrans;
    });"""
content = content.replace(mass_filter_old, mass_filter_new)

# 4. Update massTranslate API calls
mass_api_old = """            // Translate activation message
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

mass_api_new = """            // Translate activation message
            if (p.activation_message && (!p.activation_message_fr || !p.activation_message_ar || !p.activation_message_zh)) {
                const resAct = await apiCall('/api/translate', 'POST', { text: p.activation_message });
                if (!p.activation_message_fr && resAct.fr) updates.activation_message_fr = resAct.fr;
                if (!p.activation_message_ar && resAct.ar) updates.activation_message_ar = resAct.ar;
                if (!p.activation_message_zh && resAct.zh) updates.activation_message_zh = resAct.zh;
            }
            
            // Translate confirmation message
            if (p.confirmation_message && (!p.confirmation_message_fr || !p.confirmation_message_ar || !p.confirmation_message_zh)) {
                const resConf = await apiCall('/api/translate', 'POST', { text: p.confirmation_message });
                if (!p.confirmation_message_fr && resConf.fr) updates.confirmation_message_fr = resConf.fr;
                if (!p.confirmation_message_ar && resConf.ar) updates.confirmation_message_ar = resConf.ar;
                if (!p.confirmation_message_zh && resConf.zh) updates.confirmation_message_zh = resConf.zh;
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
                if (updates.confirmation_message_fr) p.confirmation_message_fr = updates.confirmation_message_fr;
                if (updates.confirmation_message_ar) p.confirmation_message_ar = updates.confirmation_message_ar;
                if (updates.confirmation_message_zh) p.confirmation_message_zh = updates.confirmation_message_zh;
                successCount++;
            }"""
content = content.replace(mass_api_old, mass_api_new)

# 5. Handle openEditModal
edit_pop_old = """    if ($('edit-prod-act-msg')) $('edit-prod-act-msg').value = p.activation_message || '';
    if ($('edit-prod-act-msg-fr')) $('edit-prod-act-msg-fr').value = p.activation_message_fr || '';
    if ($('edit-prod-act-msg-ar')) $('edit-prod-act-msg-ar').value = p.activation_message_ar || '';
    if ($('edit-prod-act-msg-zh')) $('edit-prod-act-msg-zh').value = p.activation_message_zh || '';"""

edit_pop_new = """    if ($('edit-prod-act-msg')) $('edit-prod-act-msg').value = p.activation_message || '';
    if ($('edit-prod-act-msg-fr')) $('edit-prod-act-msg-fr').value = p.activation_message_fr || '';
    if ($('edit-prod-act-msg-ar')) $('edit-prod-act-msg-ar').value = p.activation_message_ar || '';
    if ($('edit-prod-act-msg-zh')) $('edit-prod-act-msg-zh').value = p.activation_message_zh || '';
    if ($('edit-prod-conf-msg')) $('edit-prod-conf-msg').value = p.confirmation_message || '';
    if ($('edit-prod-conf-msg-fr')) $('edit-prod-conf-msg-fr').value = p.confirmation_message_fr || '';
    if ($('edit-prod-conf-msg-ar')) $('edit-prod-conf-msg-ar').value = p.confirmation_message_ar || '';
    if ($('edit-prod-conf-msg-zh')) $('edit-prod-conf-msg-zh').value = p.confirmation_message_zh || '';"""
content = content.replace(edit_pop_old, edit_pop_new)

# 6. Edit form submit
edit_sub_old = """            activation_message: $('edit-prod-act-msg') ? $('edit-prod-act-msg').value.trim() : '',
            activation_message_fr: $('edit-prod-act-msg-fr') ? $('edit-prod-act-msg-fr').value.trim() : '',
            activation_message_ar: $('edit-prod-act-msg-ar') ? $('edit-prod-act-msg-ar').value.trim() : '',
            activation_message_zh: $('edit-prod-act-msg-zh') ? $('edit-prod-act-msg-zh').value.trim() : '',
            image_url: $('edit-prod-image-url').value.trim(),"""

edit_sub_new = """            activation_message: $('edit-prod-act-msg') ? $('edit-prod-act-msg').value.trim() : '',
            activation_message_fr: $('edit-prod-act-msg-fr') ? $('edit-prod-act-msg-fr').value.trim() : '',
            activation_message_ar: $('edit-prod-act-msg-ar') ? $('edit-prod-act-msg-ar').value.trim() : '',
            activation_message_zh: $('edit-prod-act-msg-zh') ? $('edit-prod-act-msg-zh').value.trim() : '',
            confirmation_message: $('edit-prod-conf-msg') ? $('edit-prod-conf-msg').value.trim() : '',
            confirmation_message_fr: $('edit-prod-conf-msg-fr') ? $('edit-prod-conf-msg-fr').value.trim() : '',
            confirmation_message_ar: $('edit-prod-conf-msg-ar') ? $('edit-prod-conf-msg-ar').value.trim() : '',
            confirmation_message_zh: $('edit-prod-conf-msg-zh') ? $('edit-prod-conf-msg-zh').value.trim() : '',
            image_url: $('edit-prod-image-url').value.trim(),"""
content = content.replace(edit_sub_old, edit_sub_new)

# 7. Add form submit
add_sub_old = """            activation_message: $('prod-act-msg') ? $('prod-act-msg').value.trim() : '',
            activation_message_fr: $('prod-act-msg-fr') ? $('prod-act-msg-fr').value.trim() : '',
            activation_message_ar: $('prod-act-msg-ar') ? $('prod-act-msg-ar').value.trim() : '',
            activation_message_zh: $('prod-act-msg-zh') ? $('prod-act-msg-zh').value.trim() : '',
            delivery_type: $('prod-delivery-type').value"""

add_sub_new = """            activation_message: $('prod-act-msg') ? $('prod-act-msg').value.trim() : '',
            activation_message_fr: $('prod-act-msg-fr') ? $('prod-act-msg-fr').value.trim() : '',
            activation_message_ar: $('prod-act-msg-ar') ? $('prod-act-msg-ar').value.trim() : '',
            activation_message_zh: $('prod-act-msg-zh') ? $('prod-act-msg-zh').value.trim() : '',
            confirmation_message: $('prod-conf-msg') ? $('prod-conf-msg').value.trim() : '',
            confirmation_message_fr: $('prod-conf-msg-fr') ? $('prod-conf-msg-fr').value.trim() : '',
            confirmation_message_ar: $('prod-conf-msg-ar') ? $('prod-conf-msg-ar').value.trim() : '',
            confirmation_message_zh: $('prod-conf-msg-zh') ? $('prod-conf-msg-zh').value.trim() : '',
            delivery_type: $('prod-delivery-type').value"""
content = content.replace(add_sub_old, add_sub_new)

# 8. setupEvents bindings
events_old = """    const btnTranslateAdd = $('btn-translate-add');
    const btnTranslateActAdd = $('btn-translate-act-add');
    const btnTranslateEdit = $('btn-translate-edit');
    const btnTranslateActEdit = $('btn-translate-act-edit');

    if (btnTranslateAdd) btnTranslateAdd.addEventListener('click', () => autoTranslate('add', false));
    if (btnTranslateActAdd) btnTranslateActAdd.addEventListener('click', () => autoTranslate('add', true));
    if (btnTranslateEdit) btnTranslateEdit.addEventListener('click', () => autoTranslate('edit', false));
    if (btnTranslateActEdit) btnTranslateActEdit.addEventListener('click', () => autoTranslate('edit', true));"""

events_new = """    const btnTranslateAdd = $('btn-translate-add');
    const btnTranslateActAdd = $('btn-translate-act-add');
    const btnTranslateConfAdd = $('btn-translate-conf-add');
    const btnTranslateEdit = $('btn-translate-edit');
    const btnTranslateActEdit = $('btn-translate-act-edit');
    const btnTranslateConfEdit = $('btn-translate-conf-edit');

    if (btnTranslateAdd) btnTranslateAdd.addEventListener('click', () => autoTranslate('add', 'desc'));
    if (btnTranslateActAdd) btnTranslateActAdd.addEventListener('click', () => autoTranslate('add', 'act'));
    if (btnTranslateConfAdd) btnTranslateConfAdd.addEventListener('click', () => autoTranslate('add', 'conf'));
    if (btnTranslateEdit) btnTranslateEdit.addEventListener('click', () => autoTranslate('edit', 'desc'));
    if (btnTranslateActEdit) btnTranslateActEdit.addEventListener('click', () => autoTranslate('edit', 'act'));
    if (btnTranslateConfEdit) btnTranslateConfEdit.addEventListener('click', () => autoTranslate('edit', 'conf'));"""
content = content.replace(events_old, events_new)

with codecs.open('dashboard/app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("app.js fully updated with confirmation_message fields.")
