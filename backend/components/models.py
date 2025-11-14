from django.db import models
from django.contrib.auth.models import User


class ComponentCategory(models.Model):
    """Deprecated: Kept for backward compatibility if needed."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    
    class Meta:
        verbose_name_plural = "Component Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Component(models.Model):
    """Simplified CAD component with auto geometry processing"""
    CATEGORY_CHOICES = [
        ("Motor", "Motor"),
        ("Roller", "Roller"),
        ("Belt", "Belt"),
        ("Frame", "Frame"),
        ("Base", "Base"),
    ]
    
    # Editable fields
    name = models.CharField(max_length=200)
    category_label = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default="Base")
    original_file = models.FileField(upload_to='components/original/', help_text='CAD file (GLB/GLTF, STEP, STL, OBJ)')
    glb_file = models.FileField(upload_to='components/glb/', blank=True, null=True, help_text='GLB file for web visualization (converted from original if needed)')
    
    # Auto-filled geometry fields
    bounding_box = models.JSONField(default=dict, blank=True)
    center = models.JSONField(default=dict, blank=True)
    volume = models.FloatField(default=0.0)
    mountable_sides = models.JSONField(default=list, blank=True)
    supported_orientations = models.JSONField(default=list, blank=True)
    compatible_types = models.JSONField(default=list, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Processing status
    processing_status = models.CharField(
        max_length=20,
        choices=[('pending','Pending'),('processing','Processing'),('completed','Completed'),('failed','Failed')],
        default='pending'
    )
    processing_error = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['category_label', 'processing_status']),
        ]
    
    def __str__(self):
        return self.name


class ConnectionPoint(models.Model):
    """Connection points on components for assembly"""
    
    CONNECTION_TYPES = [
        ('mount', 'Mount Point'),
        ('socket', 'Socket'),
        ('screw', 'Screw Hole'),
        ('magnetic', 'Magnetic'),
        ('snap', 'Snap Fit'),
        ('custom', 'Custom'),
    ]
    
    component = models.ForeignKey(Component, on_delete=models.CASCADE, related_name='connection_points')
    name = models.CharField(max_length=100, help_text='Identifier for this connection point')
    connection_type = models.CharField(max_length=20, choices=CONNECTION_TYPES, default='mount')
    
    # Position in component's local coordinate system
    position_x = models.FloatField()
    position_y = models.FloatField()
    position_z = models.FloatField()
    
    # Normal vector (direction the connection faces)
    normal_x = models.FloatField(default=0.0)
    normal_y = models.FloatField(default=0.0)
    normal_z = models.FloatField(default=1.0)
    
    # Size and constraints
    diameter = models.FloatField(default=0.0, help_text='Connection point diameter/size')
    compatible_types = models.JSONField(default=list, help_text='List of compatible connection types')
    side_label = models.CharField(max_length=50, blank=True, help_text='Side identifier (e.g., "top", "bottom")')
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['component', 'name']
        indexes = [
            models.Index(fields=['component', 'connection_type']),
        ]
    
    def __str__(self):
        return f"{self.component.name} - {self.name}"
    
    @property
    def position(self):
        """Return position as list"""
        return [self.position_x, self.position_y, self.position_z]
    
    @property
    def normal(self):
        """Return normal vector as list"""
        return [self.normal_x, self.normal_y, self.normal_z]

