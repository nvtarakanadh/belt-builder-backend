from django.contrib import admin
from .models import Component, ComponentCategory, ConnectionPoint


@admin.register(ComponentCategory)
class ComponentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


class ConnectionPointInline(admin.TabularInline):
    model = ConnectionPoint
    extra = 0
    fields = ['name', 'connection_type', 'position_x', 'position_y', 'position_z', 'side_label']


@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_label', 'processing_status', 'created_at']
    list_filter = ['category_label', 'processing_status', 'created_at']
    search_fields = ['name']
    readonly_fields = [
        'processing_status', 'processing_error', 'created_at', 'updated_at',
        'bounding_box', 'center', 'volume', 'mountable_sides', 'supported_orientations', 'compatible_types'
    ]
    
    fields = (
        'name', 'category_label', 'original_file',
        'glb_file', 'bounding_box', 'center', 'volume',
        'mountable_sides', 'supported_orientations', 'compatible_types',
        'processing_status', 'processing_error', 'created_at', 'updated_at'
    )

