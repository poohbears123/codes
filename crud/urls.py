from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('user/list/', views.user_list, name='user_list'),
    path('user/add/', views.user_add, name='user_add'),
    path('user/edit/<int:user_id>/', views.user_edit, name='user_edit'),
    path('user/delete/<int:user_id>/', views.user_delete, name='user_delete'),
    path('user/profile/edit/', views.user_profile_edit, name='user_profile_edit'),

    path('gender/list/', views.gender_list, name='gender_list'),
    path('gender/add/', views.gender_add, name='gender_add'),
    path('gender/edit/<int:gender_id>/', views.gender_edit, name='gender_edit'),
    path('gender/delete/<int:gender_id>/', views.gender_delete, name='gender_delete'),

    path('user/change_password/', views.change_password, name='change_password'),
    path('user/change_password/success/', views.change_password_success, name='change_password_success'),
    path('user/admin_change_password/<int:user_id>/', views.admin_change_password, name='admin_change_password'),
]
from django.urls import path  
from . import views

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    path('user/list/', views.user_list, name='user_list'),
    path('user/add/', views.user_add, name='user_add'),
    path('user/edit/<int:user_id>/', views.user_edit, name='user_edit'),
    path('user/delete/<int:user_id>/', views.user_delete, name='user_delete'),

]
