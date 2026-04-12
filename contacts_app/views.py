import csv
from io import TextIOWrapper

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from openpyxl import load_workbook

from .models import Contact, Group

@login_required
def upload_contacts(request):
    """Upload a CSV or XLSX file to import contacts into a user group."""
    groups = Group.objects.filter(user=request.user).order_by('-created_at')

    if request.method == 'POST':
        group_id = request.POST.get('group')
        contact_file = request.FILES.get('contact_file')

        if not group_id or not contact_file:
            messages.error(request, "Please choose a group and upload a file.")
            return render(request, 'contacts/upload.html', {'groups': groups})

        group = Group.objects.filter(id=group_id, user=request.user).first()
        if not group:
            messages.error(request, "Selected group not found.")
            return render(request, 'contacts/upload.html', {'groups': groups})

        try:
            if contact_file.name.lower().endswith('.csv'):
                file_data = TextIOWrapper(contact_file.file, encoding='utf-8-sig')
                reader = csv.reader(file_data)
                rows = list(reader)
            elif contact_file.name.lower().endswith(('.xlsx', '.xlsm', '.xltx', '.xltm')):
                workbook = load_workbook(contact_file, read_only=True, data_only=True)
                sheet = workbook.active
                rows = [[cell for cell in row] for row in sheet.iter_rows(values_only=True)]
            else:
                raise ValueError("Unsupported file type. Please upload a .csv or .xlsx file.")
        except Exception as exc:
            messages.error(request, f"Unable to parse the file: {exc}")
            return render(request, 'contacts/upload.html', {'groups': groups})

        created_count = 0
        for row in rows:
            if not row:
                continue
            phone = str(row[0]).strip() if row[0] is not None else ''
            name = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ''
            email = str(row[2]).strip() if len(row) > 2 and row[2] is not None else ''
            if phone:
                Contact.objects.create(group=group, phone_number=phone, name=name, email=email)
                created_count += 1

        messages.success(request, f"Imported {created_count} contacts into {group.name}.")
        return redirect('dashboard')

    return render(request, 'contacts/upload.html', {'groups': groups})
