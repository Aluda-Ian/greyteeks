import re

filepath = 'campaigns/views.py'
with open(filepath, 'rb') as f:
    data = f.read()

text = data.decode('utf-8', errors='ignore')

# strip out the failed echo command at the end
text = re.sub(r'(?i)def pricing_view[\s\S]*$', '', text)
text = text.strip() + '\n\n'

new_views = """
def pricing_view(request):
    return render(request, 'home/pricing.html')

def service_view(request):
    return render(request, 'home/service.html')

def faq_view(request):
    return render(request, 'home/faq.html')
"""

text += new_views

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)

print('views.py fixed')
