import codecs

with codecs.open('dashboard/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if i == 288:
        new_lines.append("    $$('.sub-tab').forEach(t => t.addEventListener('click', () => {\n")
        new_lines.append("        t.closest('.action-bar').querySelectorAll('.sub-tab').forEach(s => s.classList.remove('active'));\n")
        new_lines.append("        t.closest('section').querySelectorAll('.sub-tab-content').forEach(c => c.classList.remove('active'));\n")
        new_lines.append("        t.classList.add('active'); \n")
        new_lines.append("        let targetContent = document.querySelector(t.getAttribute('data-sub'));\n")
        new_lines.append("        if (targetContent) targetContent.classList.add('active');\n")
        new_lines.append("    }));\n\n")
        new_lines.append("    $('btn-open-prod-modal').addEventListener('click', () => { DOM.addProdForm.reset(); DOM.prodId.value=''; if (DOM.prodDeliveryType) DOM.prodDeliveryType.value='stock'; showModal(DOM.prodModal); });\n")
        new_lines.append("    const btnMassTranslate = $('btn-mass-translate');\n")
        new_lines.append("    if (btnMassTranslate) btnMassTranslate.addEventListener('click', massTranslate);\n")
        new_lines.append("    $('btn-open-promo-modal').addEventListener('click', () => {\n")
        new_lines.append("        const sel = $('promo-products');\n")
        new_lines.append("        sel.innerHTML = '';\n")
        new_lines.append("        state.products.forEach(p => {\n")
        new_lines.append("            const lbl = document.createElement('label');\n")
        new_lines.append("            lbl.style.display = 'flex';\n")
        new_lines.append("            lbl.style.alignItems = 'center';\n")
        new_lines.append("            lbl.style.gap = '8px';\n")
        new_lines.append("            lbl.style.cursor = 'pointer';\n")
        new_lines.append("            lbl.style.margin = '0';\n")
        new_lines.append("            const cb = document.createElement('input');\n")
        new_lines.append("            cb.type = 'checkbox';\n")
        new_lines.append("            cb.value = p.id;\n")
        new_lines.append("            cb.className = 'promo-product-cb';\n")
        new_lines.append("            lbl.appendChild(cb);\n")
        new_lines.append("            lbl.appendChild(document.createTextNode(' ' + p.name));\n")
        new_lines.append("            sel.appendChild(lbl);\n")
        new_lines.append("        });\n")
        new_lines.append("        showModal(DOM.promoModal);\n")
        new_lines.append("    });\n")
        new_lines.append("    $('btn-open-binance-modal').addEventListener('click', openBinanceModal);\n")
        new_lines.append("    $$('.btn-close-modal').forEach(b => b.addEventListener('click', () => { [DOM.prodModal,DOM.stockModal,DOM.promoModal,DOM.tiersModal,DOM.orderDetailModal,DOM.viewStockModal,DOM.editProdModal,DOM.revenueModal,DOM.binanceModal,$('banModal'),$('finance-withdraw-modal'),$('finance-adjust-modal'), $('exportModal')].forEach(m => { if (m) hideModal(m); }); }));\n\n")
        skip = True
    elif i == 354: # Wait, I need to make sure I stop skipping at the right place. 
        skip = False
        new_lines.append(line)
    else:
        if not skip:
            new_lines.append(line)

with codecs.open('dashboard/app.js', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Fixed lines 288-354')
