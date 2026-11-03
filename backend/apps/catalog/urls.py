from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

# SimpleRouter ставит /products/search/ раньше /products/{slug}/, поэтому search не примут за slug.
router = SimpleRouter()
router.register("products", views.ProductViewSet, basename="product")

urlpatterns = [
    path("categories/", views.CategoryTreeView.as_view(), name="category-tree"),
    path("brands/", views.BrandListView.as_view(), name="brand-list"),
    path(
        "products/<slug:slug>/reviews/",
        views.ProductReviewsView.as_view(),
        name="product-reviews",
    ),
    *router.urls,
]
