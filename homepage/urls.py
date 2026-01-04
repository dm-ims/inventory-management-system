from django.urls import path
# Unused - django.conf.urls.url is deprecated in Django 4.0+
# from django.conf.urls import url
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('users/', views.UserView, name='users'),
    path('create-user/', views.register, name='user-create'),
    path('users/delete/<int:pk>/', views.user_delete, name='user-delete'),
    path('api/dashboard-data/', views.DashboardDataView.as_view(), name='dashboard-data'),
]