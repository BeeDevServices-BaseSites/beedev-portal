# proposalApp/urls_public.py
from django.urls import path
from . import views
from .views import *

app_name = "proposal_public"

urlpatterns = [
    path("p/<slug:token>/", views.public_proposal_view, name="proposal_public_view"),
    path("p/<slug:token>/sign/", public.public_proposal_sign, name="proposal_public_sign"),
]
