from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("me/addresses", views.AddressViewSet, basename="address")

urlpatterns = [
    path("me/", views.MeView.as_view(), name="me"),
    path("me/password/", views.ChangePasswordView.as_view(), name="me-password"),
    *router.urls,
]
