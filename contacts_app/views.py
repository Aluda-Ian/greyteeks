import csv
from io import TextIOWrapper

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from openpyxl import load_workbook

from .models import Contact, Group

@login_required
def contact_list(request):
    """List the current user's contacts with optional group filtering."""
    groups = Group.objects.filter(user=request.user).order_by('-created_at')
    group_id = request.GET.get('group')
    contacts = Contact.objects.filter(group__user=request.user).order_by('-created_at')
    selected_group = None
    if group_id:
        selected_group = groups.filter(id=group_id).first()
        if selected_group:
            contacts = contacts.filter(group=selected_group)

    return render(request, 'contacts/contact_list.html', {
        'groups': groups,
        'contacts': contacts,
        'selected_group': selected_group,
    })

@login_required
def edit_contact(request, contact_id):
    """Edit a single contact belonging to the current user."""
    contact = Contact.objects.filter(id=contact_id, group__user=request.user).first()
    if not contact:
        messages.error(request, 'Contact not found.')
        return redirect('contact_list')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        group_id = request.POST.get('group')

        if not phone_number:
            messages.error(request, 'Phone number is required.')
            return render(request, 'contacts/contact_edit.html', {
                'contact': contact,
                'groups': Group.objects.filter(user=request.user),
            })

        target_group = Group.objects.filter(id=group_id, user=request.user).first()
        if not target_group:
            messages.error(request, 'Please select a valid group.')
            return render(request, 'contacts/contact_edit.html', {
                'contact': contact,
                'groups': Group.objects.filter(user=request.user),
            })

        contact.name = name
        contact.phone_number = phone_number
        contact.email = email
        contact.group = target_group
        contact.save()
        messages.success(request, 'Contact updated successfully.')
        return redirect('contact_list')

    return render(request, 'contacts/contact_edit.html', {
        'contact': contact,
        'groups': Group.objects.filter(user=request.user),
    })

@login_required
def delete_contact(request, contact_id):
    """Delete a contact after confirmation."""
    contact = Contact.objects.filter(id=contact_id, group__user=request.user).first()
    if not contact:
        messages.error(request, 'Contact not found.')
        return redirect('contact_list')

    if request.method == 'POST':
        contact.delete()
        messages.success(request, 'Contact deleted successfully.')
        return redirect('contact_list')

    return render(request, 'contacts/contact_delete_confirm.html', {'contact': contact})

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
