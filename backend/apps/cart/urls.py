from django.urls import path

from . import views

urlpatterns = [
    path("", views.CartView.as_view(), name="cart"),
    path("merge/", views.CartMergeView.as_view(), name="cart-merge"),
    path("apply-promo/", views.ApplyPromoView.as_view(), name="cart-apply-promo"),
]
