from rest_framework import serializers
from django.conf import settings
from .models import Component, ComponentCategory, ConnectionPoint


class ConnectionPointSerializer(serializers.ModelSerializer):
    position = serializers.SerializerMethodField()
    normal = serializers.SerializerMethodField()
    
    class Meta:
        model = ConnectionPoint
        fields = [
            'id', 'name', 'connection_type', 'position', 'normal',
            'diameter', 'compatible_types', 'side_label', 'metadata'
        ]
    
    def get_position(self, obj):
        return obj.position
    
    def get_normal(self, obj):
        return obj.normal


class ComponentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ComponentCategory
        fields = ['id', 'name', 'description', 'icon']


class ComponentSerializer(serializers.ModelSerializer):
    glb_url = serializers.SerializerMethodField()
    original_url = serializers.SerializerMethodField()
    # Backward-compatible aliases for frontend
    category = serializers.CharField(source='category_label', read_only=True)
    type = serializers.CharField(source='category_label', read_only=True)
    
    class Meta:
        model = Component
        fields = [
            'id', 'name', 'category_label', 'category', 'type', 'glb_url', 'original_url',
            'bounding_box', 'center', 'volume',
            'mountable_sides', 'supported_orientations', 'compatible_types',
            'processing_status', 'processing_error', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'glb_url', 'original_url', 'bounding_box', 'center', 'volume',
            'mountable_sides', 'supported_orientations', 'compatible_types',
            'processing_status', 'processing_error', 'created_at', 'updated_at'
        ]
        # Allow name and category_label to be updated, but original_file is handled in the view
    
    def get_glb_url(self, obj):
        if obj.glb_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.glb_file.url)
            else:
                # Build absolute URL using settings if request not available
                base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
                media_url = obj.glb_file.url
                if media_url.startswith('/'):
                    return f"{base_url}{media_url}"
                return media_url
        return None
    
    def get_original_url(self, obj):
        if obj.original_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.original_file.url)
            else:
                # Build absolute URL using settings if request not available
                base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
                media_url = obj.original_file.url
                if media_url.startswith('/'):
                    return f"{base_url}{media_url}"
                return media_url
        return None


class ComponentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Component
        fields = ['name', 'category_label', 'original_file']

