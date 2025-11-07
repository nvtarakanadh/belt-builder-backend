from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ComponentViewSet, ComponentCategoryViewSet

router = DefaultRouter()
router.register(r'components', ComponentViewSet, basename='component')
router.register(r'component-categories', ComponentCategoryViewSet, basename='component-category')

urlpatterns = [
    path('', include(router.urls)),
]

