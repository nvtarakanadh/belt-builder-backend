from django.db import models
from django.contrib.auth.models import User
from components.models import Component


class Project(models.Model):
    """User project/workspace for CAD assemblies"""
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Project metadata
    metadata = models.JSONField(default=dict, blank=True)
    is_public = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['owner', '-updated_at']),
        ]
    
    def __str__(self):
        return self.name


class AssemblyItem(models.Model):
    """Individual component instance in a project assembly"""
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='assembly_items')
    component = models.ForeignKey(Component, on_delete=models.CASCADE, related_name='assembly_instances')
    
    # Transform in 3D space
    position_x = models.FloatField(default=0.0)
    position_y = models.FloatField(default=0.0)
    position_z = models.FloatField(default=0.0)
    
    # Rotation (Euler angles in degrees or quaternion)
    rotation_x = models.FloatField(default=0.0)
    rotation_y = models.FloatField(default=0.0)
    rotation_z = models.FloatField(default=0.0)
    rotation_w = models.FloatField(default=1.0, help_text='Quaternion w component')
    
    # Scale
    scale_x = models.FloatField(default=1.0)
    scale_y = models.FloatField(default=1.0)
    scale_z = models.FloatField(default=1.0)
    
    # Hierarchy (parent-child relationships)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    # Connection information
    connected_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='connected_from')
    connection_point = models.ForeignKey('components.ConnectionPoint', on_delete=models.SET_NULL, null=True, blank=True, related_name='used_in_assemblies')
    attached_at_point = models.CharField(max_length=100, blank=True, help_text='Connection point identifier where this is attached')
    
    # Metadata
    custom_name = models.CharField(max_length=200, blank=True, help_text='Custom name for this instance')
    metadata = models.JSONField(default=dict, blank=True)
    
    # Ordering
    order = models.IntegerField(default=0, help_text='Order in assembly')
    
    class Meta:
        ordering = ['project', 'order', 'id']
        indexes = [
            models.Index(fields=['project', 'parent']),
            models.Index(fields=['project', 'connected_to']),
        ]
    
    def __str__(self):
        return f"{self.project.name} - {self.component.name} ({self.custom_name or 'Instance'})"
    
    @property
    def position(self):
        """Return position as list"""
        return [self.position_x, self.position_y, self.position_z]
    
    @property
    def rotation(self):
        """Return rotation as quaternion"""
        return [self.rotation_x, self.rotation_y, self.rotation_z, self.rotation_w]
    
    @property
    def scale(self):
        """Return scale as list"""
        return [self.scale_x, self.scale_y, self.scale_z]
    
    def get_world_transform(self):
        """Calculate world transform considering parent hierarchy"""
        if self.parent:
            parent_transform = self.parent.get_world_transform()
            # Combine transforms (simplified - would need proper matrix math in production)
            return {
                'position': [
                    parent_transform['position'][0] + self.position_x,
                    parent_transform['position'][1] + self.position_y,
                    parent_transform['position'][2] + self.position_z,
                ],
                'rotation': self.rotation,  # Would need quaternion multiplication in production
                'scale': self.scale,
            }
        return {
            'position': self.position,
            'rotation': self.rotation,
            'scale': self.scale,
        }

