from django.contrib import admin
from .models import Project, AssemblyItem


class AssemblyItemInline(admin.TabularInline):
    model = AssemblyItem
    extra = 0
    fields = ['component', 'custom_name', 'position_x', 'position_y', 'position_z', 'order']
    readonly_fields = []


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'created_at', 'updated_at', 'is_public']
    list_filter = ['created_at', 'is_public']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [AssemblyItemInline]


@admin.register(AssemblyItem)
class AssemblyItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'project', 'component', 'custom_name', 'order']
    list_filter = ['project', 'component__category_label']
    search_fields = ['custom_name', 'component__name']
    raw_id_fields = ['project', 'component', 'parent', 'connected_to', 'connection_point']

