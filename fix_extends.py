import os
import re

files_to_process = [
    'manage_sms.html',
    'manage_whatsapp.html',
    'manage_mailing.html',
    'manage_users.html',
    'manage_groups.html',
    'manage_templates.html',
    'my_email_providers.html',
    'customer_groups.html'
]

base_dir = r"c:\Users\Ian Aluda\greyteeks\templates\campaigns"

def process():
    for filename in files_to_process:
        path = os.path.join(base_dir, filename)
        if not os.path.exists(path):
            print(f"File not found: {filename}")
            continue
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "{% extends" in content:
            print(f"Already extending: {filename}")
            continue
            
        match = re.search(r'<main[^>]*>(.*?)</main>', content, re.DOTALL)
        if match:
            main_content = match.group(1).strip()
            
            title_match = re.search(r'<title>(.*?)</title>', content)
            title = title_match.group(1).replace(' — Greyteeks', '') if title_match else 'Dashboard'
            
            new_content = f"{{% extends 'campaigns/dashboard.html' %}}\n\n{{% block page_title %}}{title}{{% endblock %}}\n\n{{% block content %}}\n{main_content}\n{{% endblock %}}\n"
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Processed: {filename}")
        else:
            print(f"Could not find <main> in: {filename}")

if __name__ == "__main__":
    process()
