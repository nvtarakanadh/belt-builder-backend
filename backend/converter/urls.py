"""
URL configuration for converter app
"""
from django.urls import path
from . import views

app_name = 'converter'

urlpatterns = [
    path('convert/step/', views.convert_step_to_glb, name='convert_step_to_glb'),
]


