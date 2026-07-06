import codecs

with codecs.open('dashboard/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

old_listener = "$('btn-open-prod-modal').addEventListener('click', () => { DOM.addProdForm.reset(); DOM.prodId.value=''; if (DOM.prodDeliveryType) DOM.prodDeliveryType.value='stock'; showModal(DOM.prodModal); });"

new_listener = """$('btn-open-prod-modal').addEventListener('click', () => { 
        DOM.addProdForm.reset(); 
        DOM.prodId.value=''; 
        if (DOM.prodDeliveryType) DOM.prodDeliveryType.value='stock'; 
        
        if ($('prod-act-msg')) $('prod-act-msg').value = "Your activation is complete.\\n\\nProduct: {product}\\nOrder: #{order_id}";
        if ($('prod-act-msg-fr')) $('prod-act-msg-fr').value = "Votre activation est terminée.\\n\\nProduit : {product}\\nCommande : #{order_id}";
        if ($('prod-act-msg-ar')) $('prod-act-msg-ar').value = "اكتمل التفعيل.\\n\\nالمنتج: {product}\\nالطلب: #{order_id}";
        if ($('prod-act-msg-zh')) $('prod-act-msg-zh').value = "您的激活已完成。\\n\\n产品：{product}\\n订单：#{order_id}";

        if ($('prod-conf-msg')) $('prod-conf-msg').value = "Thank you for your purchase! 🙏";
        if ($('prod-conf-msg-fr')) $('prod-conf-msg-fr').value = "Merci pour votre achat ! 🙏";
        if ($('prod-conf-msg-ar')) $('prod-conf-msg-ar').value = "شكرا لشرائك! 🙏";
        if ($('prod-conf-msg-zh')) $('prod-conf-msg-zh').value = "感谢您的购买！🙏";

        showModal(DOM.prodModal); 
    });"""

if old_listener in content:
    content = content.replace(old_listener, new_listener)
    with codecs.open('dashboard/app.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replaced old listener successfully.")
else:
    print("Old listener not found. Checking if already replaced...")
    if "Your activation is complete" in content:
        print("Already replaced.")
    else:
        print("Could not find the target string to replace.")
