from decimal import Decimal

import factory

from apps.catalog.models import Brand, Category, Product, ProductImage, ProductVariant, Review
from apps.users.tests.factories import UserFactory


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Категория {n}")
    slug = factory.Sequence(lambda n: f"category-{n}")


class BrandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Brand

    name = factory.Sequence(lambda n: f"Brand {n}")
    slug = factory.Sequence(lambda n: f"brand-{n}")


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Product {n}")
    slug = factory.Sequence(lambda n: f"product-{n}")
    description = "Описание товара"
    specs = factory.LazyFunction(lambda: {"Экран": '6,1"'})
    category = factory.SubFactory(CategoryFactory)
    brand = factory.SubFactory(BrandFactory)


class ProductVariantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductVariant

    product = factory.SubFactory(ProductFactory)
    sku = factory.Sequence(lambda n: f"SKU-{n}")
    name = "128 ГБ"
    price = Decimal("100000.00")
    stock = 5


class ProductImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductImage

    product = factory.SubFactory(ProductFactory)
    image = factory.Sequence(lambda n: f"products/photo-{n}.svg")
    alt = "фото"
    order = factory.Sequence(lambda n: n)


class ReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Review

    product = factory.SubFactory(ProductFactory)
    user = factory.SubFactory(UserFactory)
    rating = 5
    text = "Отличный товар"


def make_product(prices=("100000",), stocks=None, old_prices=None, images=1, **kwargs):
    """Товар с вариантами по списку цен (и остатков) и картинками."""
    product = ProductFactory(**kwargs)
    stocks = stocks or [5] * len(prices)
    old_prices = old_prices or [None] * len(prices)
    for price, stock, old_price in zip(prices, stocks, old_prices, strict=True):
        ProductVariantFactory(
            product=product,
            price=Decimal(price),
            stock=stock,
            old_price=Decimal(old_price) if old_price else None,
        )
    for n in range(images):
        ProductImageFactory(product=product, order=n + 1, image=f"products/{product.slug}-{n}.svg")
    return product
