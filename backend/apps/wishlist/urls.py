from django.urls import path

from . import views

urlpatterns = [
    path("", views.WishlistView.as_view(), name="wishlist"),
    path("<int:product_id>/", views.WishlistItemView.as_view(), name="wishlist-item"),
]
