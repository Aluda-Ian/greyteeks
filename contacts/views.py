import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Contact, Group

def upload_contacts(request):
    if request.method == "POST" and request.FILES.get('contact_file'):
        file = request.FILES['contact_file']
        group_id = request.POST.get('group')
        
        try:
            group = Group.objects.get(id=group_id)
            
            # Read the file based on its extension
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)

            # Standardize column names to lowercase to avoid errors
            df.columns = [c.lower().strip() for c in df.columns]

            contacts_created = 0
            for _, row in df.iterrows():
                # We expect columns named 'name' and 'phone'
                phone = str(row.get('phone', '')).strip()
                if phone:
                    Contact.objects.create(
                        group=group,
                        name=row.get('name', 'Unknown'),
                        phone_number=phone,
                        email=row.get('email', '')
                    )
                    contacts_created += 1
            
            messages.success(request, f"Successfully imported {contacts_created} contacts to {group.name}!")
            return redirect('dashboard')
            
        except Exception as e:
            messages.error(request, f"Error processing file: {e}")

    groups = Group.objects.all()
    return render(request, 'contacts/upload.html', {'groups': groups})