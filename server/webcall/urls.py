from django.urls import path
from .views import (
    create_offer,
    get_offer,
    create_answer,
    get_answer,
    store_ice_candidate,
    get_ice_candidates,
)

urlpatterns = [
    path("offer/", create_offer, name="create_offer"),
    path("offer/get/", get_offer, name="get_offer"),
    path("answer/", create_answer, name="create_answer"),
    path("answer/get/", get_answer, name="get_answer"),
    path("candidate/", store_ice_candidate, name="store_ice_candidate"),
    path("candidate/get/", get_ice_candidates, name="get_ice_candidates"),
]
