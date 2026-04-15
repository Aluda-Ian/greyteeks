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
            continue
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replaces the {% if messages %} block
        pattern = r'{%\s*if messages\s*%}.*?{%\s*endif\s*%}'
        content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Cleaned messages from: {filename}")

if __name__ == "__main__":
    process()
