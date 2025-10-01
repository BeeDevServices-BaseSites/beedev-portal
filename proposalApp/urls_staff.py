from django.urls import path, reverse_lazy
from . import views
from .views import *
from django.conf import settings
from django.conf.urls.static import static

# All urls are at base/proposals/

app_name = "proposal_staff"

urlpatterns = [
    path('', views.proposal_home, name='proposal_home'),
    path('draft/new/', views.create_new_draft, name='create_new_draft'),
    path('draft/<int:pk>/', views.view_draft_detail, name='draft_detail'),
    path('proposal/<int:pk>/', views.view_proposal_detail, name="proposal_detail"),
    path("proposal/<int:pk>/pdf/generate/", views.generate_proposal_pdf_view, name="proposal_generate_pdf"),
    path("proposal/<int:pk>/pdf/", views.view_proposal_pdf, name="proposal_pdf"),
    path("proposals/<int:pk>/send/", views.send_proposal, name="proposal_send"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)