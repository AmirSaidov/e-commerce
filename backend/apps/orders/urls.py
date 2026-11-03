from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("", views.OrderViewSet, basename="order")

urlpatterns = router.urls
