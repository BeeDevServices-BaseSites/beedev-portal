from django.urls import path, reverse_lazy
from .import views
from .views import *
from django.conf import settings
from django.conf.urls.static import static

# All urls are at base/staff/companies

app_name = "company_staff"

urlpatterns = [
    #  || General Links ||


    # || Staff/Employee Links ||
    path('', views.company_home, name="company_home"),
    path('company/<int:pk>/', views.view_company_detail, name="company_detail"),
    path('company/<int:pk>/edit_info/', views.company_edit, name="company_edit_details"),
    path('company/<int:pk>/edit_status/', views.company_status, name="edit_company_status"),
    path('company/<int:pk>/edit_progress/', views.progress_update, name="progress_update"),
    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)