from rest_framework import serializers
from .models import Project, AssemblyItem
from components.models import Component
from components.serializers import ComponentSerializer, ConnectionPointSerializer


class AssemblyItemSerializer(serializers.ModelSerializer):
    component = ComponentSerializer(read_only=True)
    component_id = serializers.PrimaryKeyRelatedField(
        queryset=Component.objects.all(),
        source='component',
        write_only=True,
        required=True
    )
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=AssemblyItem.objects.all(),
        source='parent',
        write_only=True,
        required=False,
        allow_null=True
    )
    connected_to_id = serializers.PrimaryKeyRelatedField(
        queryset=AssemblyItem.objects.all(),
        source='connected_to',
        write_only=True,
        required=False,
        allow_null=True
    )
    position = serializers.SerializerMethodField()
    rotation = serializers.SerializerMethodField()
    scale = serializers.SerializerMethodField()
    world_transform = serializers.SerializerMethodField()
    connection_point_details = ConnectionPointSerializer(source='connection_point', read_only=True)
    
    class Meta:
        model = AssemblyItem
        fields = [
            'id', 'component', 'component_id', 'custom_name',
            'position_x', 'position_y', 'position_z',
            'rotation_x', 'rotation_y', 'rotation_z', 'rotation_w',
            'scale_x', 'scale_y', 'scale_z',
            'position', 'rotation', 'scale',
            'parent_id', 'connected_to_id', 'connected_to',
            'connection_point', 'connection_point_details', 'attached_at_point',
            'metadata', 'order', 'world_transform'
        ]
        read_only_fields = ['id', 'connected_to']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure nested ComponentSerializer gets the request context
        if 'component' in self.fields and isinstance(self.fields['component'], ComponentSerializer):
            # The context is automatically passed to nested serializers in DRF
            pass
        # Set queryset for project-specific items
        if self.context.get('project'):
            project = self.context['project']
            self.fields['component_id'].queryset = None  # All components
            self.fields['parent_id'].queryset = AssemblyItem.objects.filter(project=project)
            self.fields['connected_to_id'].queryset = AssemblyItem.objects.filter(project=project)
    
    def get_position(self, obj):
        return obj.position
    
    def get_rotation(self, obj):
        return obj.rotation
    
    def get_scale(self, obj):
        return obj.scale
    
    def get_world_transform(self, obj):
        return obj.get_world_transform()


class ProjectSerializer(serializers.ModelSerializer):
    assembly_items = AssemblyItemSerializer(many=True, read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'owner', 'owner_username',
            'created_at', 'updated_at', 'metadata', 'is_public',
            'assembly_items'
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at']


class ProjectListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for project lists"""
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'owner_username',
            'created_at', 'updated_at', 'is_public', 'item_count'
        ]
    
    def get_item_count(self, obj):
        return obj.assembly_items.count()


class AssemblyItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating assembly items"""
    component_id = serializers.IntegerField(write_only=True)
    parent_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = AssemblyItem
        fields = [
            'component_id', 'custom_name',
            'position_x', 'position_y', 'position_z',
            'rotation_x', 'rotation_y', 'rotation_z', 'rotation_w',
            'scale_x', 'scale_y', 'scale_z',
            'parent_id', 'attached_at_point', 'metadata', 'order'
        ]

