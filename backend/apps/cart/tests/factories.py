from decimal import Decimal

import factory

from apps.cart.models import PromoCode


class PromoCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PromoCode
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: f"PROMO{n}")
    type = PromoCode.Type.PERCENT
    value = Decimal("10")
