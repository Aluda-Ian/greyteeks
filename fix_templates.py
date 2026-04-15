import os

def fix_sms():
    path = 'templates/campaigns/manage_sms.html'
    if not os.path.exists(path): return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Form handling
    content = content.replace('<h5 class="fw-bold mb-3">Add SMS Provider</h5>', '{% if edit_provider %}<h5 class="fw-bold mb-3">Edit SMS Provider</h5>{% else %}<h5 class="fw-bold mb-3">Add SMS Provider</h5>{% endif %}')
    content = content.replace('<input type="hidden" name="action" value="create_provider">', '{% if edit_provider %}<input type="hidden" name="provider_id" value="{{ edit_provider.id }}"><input type="hidden" name="action" value="update_provider">{% else %}<input type="hidden" name="action" value="create_provider">{% endif %}')

    content = content.replace('<option value="africas_talking">', '<option value="africas_talking" {% if edit_provider.name == "africas_talking" %}selected{% endif %}>')
    content = content.replace('<option value="twilio">', '<option value="twilio" {% if edit_provider.name == "twilio" %}selected{% endif %}>')
    content = content.replace('<option value="infobip">', '<option value="infobip" {% if edit_provider.name == "infobip" %}selected{% endif %}>')
    
    content = content.replace('name="api_key" class="form-control" required>', 'name="api_key" class="form-control" value="{{ edit_provider.api_key|default:\'\' }}" required>')
    content = content.replace('name="username" class="form-control" required>', 'name="username" class="form-control" value="{{ edit_provider.username|default:\'\' }}" required>')
    content = content.replace('name="sender_id" class="form-control">', 'name="sender_id" class="form-control" value="{{ edit_provider.sender_id|default:\'\' }}">')
    
    content = content.replace('<button type="submit" class="btn btn-primary w-100">Add Provider</button>', '<button type="submit" class="btn btn-primary w-100">{% if edit_provider %}Update{% else %}Add{% endif %} Provider</button>\n                                    {% if edit_provider %}<a href="{% url \'manage_sms\' %}" class="btn btn-outline-secondary w-100 mt-2">Cancel</a>{% endif %}')

    content = content.replace('<form method="post" class="d-inline-block">\n                                                        {% csrf_token %}\n                                                        <input type="hidden" name="provider_id" value="{{ provider.id }}">\n                                                        <input type="hidden" name="action" value="toggle_provider">', '<a href="?edit_provider_id={{ provider.id }}" class="btn btn-sm btn-outline-primary rounded-3 me-2">Edit</a>\n                                                    <form method="post" class="d-inline-block">\n                                                        {% csrf_token %}\n                                                        <input type="hidden" name="provider_id" value="{{ provider.id }}">\n                                                        <input type="hidden" name="action" value="toggle_provider">')
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_whatsapp():
    path = 'templates/campaigns/manage_whatsapp.html'
    if not os.path.exists(path): return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace('<h5 class="fw-bold mb-3">Add WhatsApp Provider</h5>', '{% if edit_provider %}<h5 class="fw-bold mb-3">Edit WhatsApp Provider</h5>{% else %}<h5 class="fw-bold mb-3">Add WhatsApp Provider</h5>{% endif %}')
    content = content.replace('<input type="hidden" name="action" value="create_provider">', '{% if edit_provider %}<input type="hidden" name="provider_id" value="{{ edit_provider.id }}"><input type="hidden" name="action" value="update_provider">{% else %}<input type="hidden" name="action" value="create_provider">{% endif %}')

    content = content.replace('<option value="meta">', '<option value="meta" {% if edit_provider.provider_type == "meta" %}selected{% endif %}>')
    content = content.replace('<option value="infobip">', '<option value="infobip" {% if edit_provider.provider_type == "infobip" %}selected{% endif %}>')
    content = content.replace('name="name" class="form-control" placeholder="Meta Cloud API" value="Meta Cloud API">', 'name="name" class="form-control" placeholder="Meta Cloud API" value="{{ edit_provider.name|default:\'Meta Cloud API\' }}">')
    
    content = content.replace('name="access_token" class="form-control" required>', 'name="access_token" class="form-control" value="{{ edit_provider.access_token|default:\'\' }}" required>')
    content = content.replace('name="phone_number_id" class="form-control">', 'name="phone_number_id" class="form-control" value="{{ edit_provider.phone_number_id|default:\'\' }}">')
    content = content.replace('name="waba_id" class="form-control">', 'name="waba_id" class="form-control" value="{{ edit_provider.waba_id|default:\'\' }}">')
    content = content.replace('name="infobip_base_url" class="form-control" placeholder="xyz.api.infobip.com">', 'name="infobip_base_url" class="form-control" value="{{ edit_provider.infobip_base_url|default:\'\' }}" placeholder="xyz.api.infobip.com">')
    content = content.replace('name="infobip_sender" class="form-control" placeholder="WhatsApp Sender ID">', 'name="infobip_sender" class="form-control" value="{{ edit_provider.infobip_sender|default:\'\' }}" placeholder="WhatsApp Sender ID">')

    content = content.replace('<button type="submit" class="btn btn-primary w-100">Add Provider</button>', '<button type="submit" class="btn btn-primary w-100">{% if edit_provider %}Update{% else %}Add{% endif %} Provider</button>\n                                    {% if edit_provider %}<a href="{% url \'manage_whatsapp\' %}" class="btn btn-outline-secondary w-100 mt-2">Cancel</a>{% endif %}')
    
    content = content.replace('<form method="post" class="d-inline-block">\n                                                        {% csrf_token %}\n                                                        <input type="hidden" name="provider_id" value="{{ provider.id }}">\n                                                        <input type="hidden" name="action" value="toggle_provider">', '<a href="?edit_provider_id={{ provider.id }}" class="btn btn-sm btn-outline-primary rounded-3 me-2">Edit</a>\n                                                    <form method="post" class="d-inline-block">\n                                                        {% csrf_token %}\n                                                        <input type="hidden" name="provider_id" value="{{ provider.id }}">\n                                                        <input type="hidden" name="action" value="toggle_provider">')

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def fix_email():
    path = 'templates/campaigns/my_email_providers.html'
    if not os.path.exists(path): return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace('<h5 class="fw-bold mb-3">Add Email Provider</h5>', '{% if edit_provider %}<h5 class="fw-bold mb-3">Edit Email Provider</h5>{% else %}<h5 class="fw-bold mb-3">Add Email Provider</h5>{% endif %}')
    content = content.replace('<input type="hidden" name="action" value="create_provider">', '{% if edit_provider %}<input type="hidden" name="provider_id" value="{{ edit_provider.id }}"><input type="hidden" name="action" value="update_provider">{% else %}<input type="hidden" name="action" value="create_provider">{% endif %}')

    content = content.replace('name="name" class="form-control" required>', 'name="name" class="form-control" value="{{ edit_provider.name|default:\'\' }}" required>')
    content = content.replace('name="smtp_host" class="form-control" required>', 'name="smtp_host" class="form-control" value="{{ edit_provider.smtp_host|default:\'\' }}" required>')
    content = content.replace('name="smtp_port" class="form-control" value="587" required>', 'name="smtp_port" class="form-control" value="{{ edit_provider.smtp_port|default:\'587\' }}" required>')
    content = content.replace('name="smtp_username" class="form-control" required>', 'name="smtp_username" class="form-control" value="{{ edit_provider.smtp_username|default:\'\' }}" required>')
    content = content.replace('name="smtp_password" class="form-control" required>', 'name="smtp_password" class="form-control" value="{{ edit_provider.smtp_password|default:\'\' }}" required>')
    content = content.replace('name="from_email" class="form-control" required>', 'name="from_email" class="form-control" value="{{ edit_provider.from_email|default:\'\' }}" required>')
    
    content = content.replace('name="use_tls" class="form-check-input" checked>', 'name="use_tls" class="form-check-input" {% if not edit_provider or edit_provider.use_tls %}checked{% endif %}>')
    content = content.replace('name="use_ssl" class="form-check-input">', 'name="use_ssl" class="form-check-input" {% if edit_provider and edit_provider.use_ssl %}checked{% endif %}>')

    if '<button type="submit" class="btn btn-primary w-100">Save Provider</button>' in content:
        content = content.replace('<button type="submit" class="btn btn-primary w-100">Save Provider</button>', '<button type="submit" class="btn btn-primary w-100">{% if edit_provider %}Update{% else %}Save{% endif %} Provider</button>\n                                    {% if edit_provider %}<a href="{% url \'my_email_providers\' %}" class="btn btn-outline-secondary w-100 mt-2">Cancel</a>{% endif %}')
    else:
        content = content.replace('<button type="submit" class="btn btn-primary w-100">Add Provider</button>', '<button type="submit" class="btn btn-primary w-100">{% if edit_provider %}Update{% else %}Add{% endif %} Provider</button>\n                                    {% if edit_provider %}<a href="{% url \'my_email_providers\' %}" class="btn btn-outline-secondary w-100 mt-2">Cancel</a>{% endif %}')

    content = content.replace('<form method="post" class="d-inline-block">\n                                                        {% csrf_token %}\n                                                        <input type="hidden" name="provider_id" value="{{ provider.id }}">\n                                                        <input type="hidden" name="action" value="toggle_provider">', '<a href="?edit_provider_id={{ provider.id }}" class="btn btn-sm btn-outline-primary rounded-3 me-2">Edit</a>\n                                                    <form method="post" class="d-inline-block">\n                                                        {% csrf_token %}\n                                                        <input type="hidden" name="provider_id" value="{{ provider.id }}">\n                                                        <input type="hidden" name="action" value="toggle_provider">')
                                                        
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

fix_sms()
fix_whatsapp()
fix_email()
print("Done")
