# recommendox/urls.py
from django.urls import path
from . import views

app_name = 'recommendox'

urlpatterns = [
    # ========== PUBLIC PAGES ==========
    path('', views.home, name='home'),  # This becomes http://127.0.0.1:8000/admin/ (wrong!)
    
    # Change your home page to be separate:
    # path('home/', views.home, name='home'),  # Now http://127.0.0.1:8000/admin/home/
    
    path('browse/', views.content_list, name='content_list'),
    path('content/<int:content_id>/', views.content_detail, name='content_detail'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # ========== USER PAGES ==========
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('watchlist/manage/', views.manage_watchlist, name='manage_watchlist'),
    path('content/<int:content_id>/rate/', views.rate_content, name='rate_content'),
    path('content/<int:content_id>/review/', views.add_review, name='add_review'),
    
    # ========== ADMIN PAGES ==========
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-manage-content/', views.manage_content, name='manage_content'),
    path('admin-manage-users/', views.manage_users, name='manage_users'),
    path('admin-moderate-reviews/', views.moderate_reviews, name='moderate_reviews'),
    path('admin/manage-content/edit/<int:content_id>/', views.edit_content, name='edit_content'),
    path('admin/manage-content/delete/<int:content_id>/', views.delete_content, name='delete_content'),

    # recommendox/urls.py - Add these URLs
    path('review/edit/<int:review_id>/', views.edit_review, name='edit_review'),
    path('review/delete/<int:review_id>/', views.delete_review, name='delete_review'),
    path('admin/make-reviewer/<int:user_id>/', views.make_reviewer, name='make_reviewer'),

    # recommendox/urls.py - Add these URLs
    path('creator/dashboard/', views.creator_dashboard, name='creator_dashboard'),
    path('admin/make-creator/<int:user_id>/', views.make_creator, name='make_creator'),

    # recommendox/urls.py - Add these URLs

    # recommendox/urls.py
    path('ott/browse/', views.ott_browse, name='ott_browse'),
]