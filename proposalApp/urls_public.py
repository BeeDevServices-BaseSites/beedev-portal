# proposalApp/urls_public.py
from django.urls import path
from .views import public

app_name = "proposal_public"

urlpatterns = [
    path("proposals/s/<str:token>/", public.public_proposal_view, name="view"),
    path("proposals/s/<str:token>/pdf/", public.public_proposal_pdf, name="pdf"),
]
