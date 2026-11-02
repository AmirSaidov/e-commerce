from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

api_v1 = [
    path("", include("apps.core.urls")),
    path("auth/", include("apps.users.auth_urls")),
    path("users/", include("apps.users.urls")),
    path("wishlist/", include("apps.wishlist.urls")),
    path("cart/", include("apps.cart.urls")),
    path("orders/", include("apps.orders.urls")),
    path("payments/", include("apps.payments.urls")),
    path("", include("apps.catalog.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

if settings.SERVE_MEDIA:
    # static() работает только при DEBUG; при local-хранилище медиа отдаём и в проде.
    urlpatterns.append(
        re_path(
            rf"^{settings.MEDIA_URL.strip('/')}/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        )
    )

# Весь сайт — API, поэтому даже ошибки вне DRF отдаём JSON в формате {detail, code, fields}.
handler400 = "apps.core.views.bad_request"
handler403 = "apps.core.views.permission_denied"
handler404 = "apps.core.views.page_not_found"
handler500 = "apps.core.views.server_error"
