from django.contrib import admin
from .models import Group, Contact

class ContactInline(admin.TabularInline):
    model = Contact
    extra = 0
    fields = ('name', 'phone_number', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    list_filter = ('user',)
    search_fields = ('name', 'description', 'user__username')
    inlines = [ContactInline]

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'group', 'created_at')
    list_filter = ('group', 'created_at')
    search_fields = ('name', 'phone_number', 'group__name')
