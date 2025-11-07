from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet, AssemblyItemViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'assembly-items', AssemblyItemViewSet, basename='assembly-item')

urlpatterns = [
    path('', include(router.urls)),
]

