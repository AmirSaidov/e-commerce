from django.urls import path

from . import views

urlpatterns = [
    path("checkout-session/", views.CheckoutSessionView.as_view(), name="checkout-session"),
    path("webhook/", views.StripeWebhookView.as_view(), name="stripe-webhook"),
]
