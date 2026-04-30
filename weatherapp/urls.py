from django.urls import path
from .import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('weather/', views.home, name='weather-home'),
    path('index/', views.home),
    path('features/', views.features, name='features'),
    path('about/', views.about, name='about'),
    path('demo/', views.demo, name='demo'),
    path('api/suggestions/', views.city_suggestions, name='city-suggestions'),
]
