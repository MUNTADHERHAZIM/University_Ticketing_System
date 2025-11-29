from django.urls import path
from . import views

urlpatterns = [
    path('', views.notifications_list, name='notifications_list'),
    path('api/', views.notifications_api, name='notifications_api'),
    path('mark-read/', views.mark_as_read, name='mark_notifications_read'),
    path('create/', views.create_notification, name='create_notification'),
    path('mark-all-read/', views.mark_all_as_read, name='mark_all_notifications_read'),
    path('edit/<int:pk>/', views.edit_notification, name='edit_notification'),
]
