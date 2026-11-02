"""Демо-данные из каталога фронта.

    python manage.py seed                     # из клона фронта рядом (../frontend-readonly)
    python manage.py seed --catalog PATH      # свой путь к catalog.json (+ --images DIR)
    python manage.py seed --github            # прод: прямо из GitHub-репозитория фронта
    python manage.py seed --github --if-empty # то же, но только если каталог ещё пуст

Команда идемпотентна: всё ищется по slug / sku / email и обновляется, дубли не появляются.
Картинки копируются (не перемещаются) из frontend/public/mock в хранилище медиа
(папка media/ или R2); уже скопированные не перезаписываются.
"""

import json
import math
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.cart.models import PromoCode
from apps.catalog.models import Brand, Category, Product, ProductImage, ProductVariant, Review
from apps.users.models import User

DEFAULT_CATALOG = (
    settings.BASE_DIR.parent / "frontend-readonly" / "frontend" / "src/lib/mock/catalog.json"
)

# Репозиторий фронта, закреплённый на коммите, с которым сверялся контракт: seed на проде не
# зависит от того, что потом попадёт в main. Другой коммит или ветка: --github <ref>.
FRONTEND_REPO_RAW = "https://raw.githubusercontent.com/AmirSaidov/e-commerce/{ref}/frontend"
FRONTEND_REF = "6457c049b0722fb8ac88f33899f5e23ea72f65ea"
DOWNLOAD_TIMEOUT = 30
DOWNLOAD_WORKERS = 8

DEMO_EMAIL = "demo@voltra.kz"
DEMO_PASSWORD = "demo12345"
IMAGES_PER_PRODUCT = 3

# Промокоды из ТЗ и мока фронта (PROMO_CODES в frontend/src/lib/mock/backend.ts).
PROMO_CODES = [
    {"code": "WELCOME10", "type": "percent", "value": Decimal("10"), "expires_at": None},
    {"code": "VOLTRA5000", "type": "fixed", "value": Decimal("5000"), "expires_at": None},
    {
        "code": "SUMMER25",
        "type": "percent",
        "value": Decimal("25"),
        "expires_at": datetime(2025, 8, 31, 18, 59, 59, tzinfo=UTC),  # истёк
    },
]

# Отзывы повторяют мок фронта (frontend/src/lib/mock/catalog.ts), чтобы рейтинги и число отзывов
# совпадали с демо-режимом. Авторы — неактивные пользователи без пароля.
REVIEWERS = [
    ("Айгерим", "Сапарова"),
    ("Данияр", "Касымов"),
    ("Мария", "Петрова"),
    ("Тимур", "Ахметов"),
    ("Алина", "Жумабаева"),
    ("Ерлан", "Беков"),
    ("Ольга", "Волкова"),
    ("Нурлан", "Муратов"),
]
REVIEW_TEXTS = [
    "Пользуюсь уже месяц — полностью доволен. Доставили на следующий день, "
    "всё упаковано аккуратно.",
    "Отличное качество сборки, работает быстро. За свои деньги лучше варианта не нашёл.",
    "Хороший товар, но хотелось бы чуть больше времени автономной работы. В остальном всё супер.",
    "Брал в подарок — очень понравилось. Магазину спасибо за быструю доставку и консультацию.",
    "Сравнивал с конкурентами, остановился на этом и не пожалел. Рекомендую.",
    "Всё как в описании. Настроил за пять минут, пользоваться удобно.",
    "Качество отличное, но коробка пришла слегка помятой. Сам товар в идеальном состоянии.",
    "Второй раз покупаю здесь — цены ниже, чем в других магазинах, и всё оригинальное.",
]


def js_round(value):
    """Math.round из JS (половина — вверх), чтобы числа совпали с моком фронта."""
    return math.floor(value + 0.5)


def download(url):
    """Содержимое файла по URL или None, если его нет (404)."""
    try:
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise CommandError(f"Не удалось скачать {url}: HTTP {exc.code}") from exc
    except OSError as exc:
        raise CommandError(f"Не удалось скачать {url}: {exc}") from exc


def image_paths(data):
    """Пути картинок каталога внутри public/mock (они же имена в хранилище медиа)."""
    paths = [f"categories/{row['slug']}.svg" for row in data["categories"]]
    for row in data["products"]:
        paths += [f"products/{row['slug']}-{n}.svg" for n in range(1, IMAGES_PER_PRODUCT + 1)]
    return paths


class LocalSource:
    """Клон фронта на диске (локальная разработка)."""

    def __init__(self, catalog, images):
        self.catalog = Path(catalog).resolve()
        if not self.catalog.is_file():
            raise CommandError(f"Не найден каталог {self.catalog}. Укажите путь через --catalog.")
        self.images = Path(images).resolve() if images else self.catalog.parents[3] / "public/mock"
        if not self.images.is_dir():
            raise CommandError(f"Не найдена папка картинок {self.images}. Укажите --images.")

    def __str__(self):
        return str(self.catalog)

    def read_catalog(self):
        return self.catalog.read_bytes()

    def prefetch(self, relatives):
        pass  # с диска читаем по мере надобности

    def read_image(self, relative):
        path = self.images / relative
        return path.read_bytes() if path.is_file() else None


class GitHubSource:
    """Публичный репозиторий фронта на GitHub (прод, где клона нет)."""

    def __init__(self, ref):
        self.base = FRONTEND_REPO_RAW.format(ref=ref)
        self.cache = {}

    def __str__(self):
        return f"{self.base}/src/lib/mock/catalog.json"

    def read_catalog(self):
        data = download(str(self))
        if data is None:
            raise CommandError(f"Не найден каталог {self}.")
        return data

    def prefetch(self, relatives):
        """Скачивает картинки параллельно: по одной ~120 файлов идут больше минуты."""
        with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
            contents = pool.map(self._url_content, relatives)
            for relative, content in zip(relatives, contents, strict=True):
                self.cache[relative] = content

    def _url_content(self, relative):
        return download(f"{self.base}/public/mock/{relative}")

    def read_image(self, relative):
        if relative not in self.cache:
            self.cache[relative] = self._url_content(relative)
        return self.cache[relative]


class Command(BaseCommand):
    help = "Заполняет каталог, демо-пользователя и отзывы из catalog.json фронта."

    def add_arguments(self, parser):
        parser.add_argument(
            "--catalog",
            type=Path,
            default=DEFAULT_CATALOG,
            help="путь к frontend/src/lib/mock/catalog.json (по умолчанию — клон фронта рядом)",
        )
        parser.add_argument(
            "--images",
            type=Path,
            default=None,
            help="папка frontend/public/mock (по умолчанию вычисляется из --catalog)",
        )
        parser.add_argument(
            "--github",
            nargs="?",
            const=FRONTEND_REF,
            default=None,
            metavar="REF",
            help="брать каталог и картинки из GitHub-репозитория фронта (прод без клона)",
        )
        parser.add_argument(
            "--if-empty",
            action="store_true",
            help="ничего не делать, если товары уже есть (для запуска при каждом старте)",
        )

    def handle(self, *args, **options):
        if options["if_empty"] and Product.objects.exists():
            self.stdout.write("Каталог уже заполнен — seed пропущен (--if-empty).")
            return
        if options["github"]:
            self.source = GitHubSource(options["github"])
        else:
            self.source = LocalSource(options["catalog"], options["images"])

        data = json.loads(self.source.read_catalog().decode("utf-8"))
        self.stats = Counter()
        # Сеть — до транзакции и только для тех файлов, которых ещё нет в хранилище.
        self.source.prefetch(
            [path for path in image_paths(data) if not default_storage.exists(path)]
        )

        with transaction.atomic():
            categories = self.seed_categories(data["categories"])
            brands = self.seed_brands(data["brands"])
            products = self.seed_products(data["products"], categories, brands)
            self.seed_demo_user()
            self.seed_promo_codes()
            self.seed_reviews(data["products"], products)

        self.report()

    # ---------- каталог ----------

    def seed_categories(self, rows):
        categories = {}
        for order, row in enumerate(rows):
            categories[row["slug"]] = self.upsert(
                Category,
                "categories",
                slug=row["slug"],
                defaults={
                    "name": row["name"],
                    "order": order,
                    "image": self.copy_image(
                        f"categories/{row['slug']}.svg", f"categories/{row['slug']}.svg"
                    ),
                },
            )
        # Родителей проставляем вторым проходом: порядок строк в файле не важен.
        for row in rows:
            category = categories[row["slug"]]
            parent = categories[row["parent"]] if row["parent"] else None
            if category.parent_id != (parent.pk if parent else None):
                category.parent = parent
                category.save(update_fields=["parent"])
        return categories

    def seed_brands(self, rows):
        return {
            row["slug"]: self.upsert(
                Brand, "brands", slug=row["slug"], defaults={"name": row["name"]}
            )
            for row in rows
        }

    def seed_products(self, rows, categories, brands):
        products = {}
        for row in rows:
            slug = row["slug"]
            product = self.upsert(
                Product,
                "products",
                slug=slug,
                defaults={
                    "name": row["name"],
                    "description": row["description"],
                    "specs": {k: v for k, v in row["specs"].items() if isinstance(v, str)},
                    "category": categories[row["category"]],
                    "brand": brands[row["brand"]],
                    "popularity": row["popularity"],
                    "is_active": True,
                    "created_at": datetime.fromisoformat(row["created"]).replace(tzinfo=UTC),
                },
            )
            products[slug] = product

            for index, variant in enumerate(row["variants"], start=1):
                old_price = row["old_price"]
                self.upsert(
                    ProductVariant,
                    "variants",
                    # В моке фронта sku обрезан до 10 символов и даёт коллизии — берём весь slug.
                    sku=f"{slug.upper()}-{index}",
                    defaults={
                        "product": product,
                        "name": variant["name"],
                        "price": Decimal(row["price"] + variant["delta"]),
                        "old_price": (Decimal(old_price + variant["delta"]) if old_price else None),
                        "stock": variant["stock"],
                    },
                )

            for n in range(1, IMAGES_PER_PRODUCT + 1):
                image = self.copy_image(f"products/{slug}-{n}.svg", f"products/{slug}-{n}.svg")
                if image:
                    self.upsert(
                        ProductImage,
                        "images",
                        product=product,
                        order=n,
                        defaults={"image": image, "alt": f"{row['name']} — фото {n}"},
                    )
        return products

    # ---------- промокоды ----------

    def seed_promo_codes(self):
        for row in PROMO_CODES:
            code, defaults = row["code"], {k: v for k, v in row.items() if k != "code"}
            self.upsert(PromoCode, "promo", code=code, defaults={**defaults, "is_active": True})

    # ---------- пользователи и отзывы ----------

    def seed_demo_user(self):
        user = self.upsert(
            User,
            "users",
            email=DEMO_EMAIL,
            defaults={
                "first_name": "Демо",
                "last_name": "Покупатель",
                "phone": "",
                "is_active": True,
                "is_email_verified": True,
            },
        )
        # Пароль задаём при каждом запуске: демо-вход всегда работает.
        user.set_password(DEMO_PASSWORD)
        user.save(update_fields=["password"])

    def seed_reviews(self, rows, products):
        reviewers = []
        for index, (first_name, last_name) in enumerate(REVIEWERS, start=1):
            reviewer = self.upsert(
                User,
                "reviewers",
                email=f"reviewer{index}@demo.voltra.kz",
                defaults={"first_name": first_name, "last_name": last_name, "is_active": False},
            )
            if reviewer.has_usable_password():
                reviewer.set_unusable_password()
                reviewer.save(update_fields=["password"])
            reviewers.append(reviewer)

        now = timezone.now()
        for i, row in enumerate(rows):
            product = products[row["slug"]]
            created = product.created_at
            count = max(2, js_round(row["popularity"] / 12))
            fives = min(count, js_round((row["rating"] - 4) * count))
            for k in range(count):
                self.upsert(
                    Review,
                    "reviews",
                    product=product,
                    user=reviewers[(i + k) % len(reviewers)],
                    defaults={
                        "rating": 5 if k < fives else 4,
                        "text": REVIEW_TEXTS[(i * 3 + k) % len(REVIEW_TEXTS)],
                        "created_at": min(created + timedelta(days=6 * (k + 1)), now),
                    },
                )

    # ---------- служебное ----------

    def upsert(self, model, label, defaults, **lookup):
        obj, created = model.objects.update_or_create(defaults=defaults, **lookup)
        self.stats[f"{label}_{'created' if created else 'updated'}"] += 1
        return obj

    def copy_image(self, source, name):
        """Копирует файл из public/mock фронта в хранилище; уже скопированный не трогает."""
        if default_storage.exists(name):
            self.stats["files_kept"] += 1
            return name
        content = self.source.read_image(source)
        if content is None:
            self.stderr.write(self.style.WARNING(f"Нет картинки {source}, пропускаю"))
            self.stats["images_missing"] += 1
            return ""
        saved = default_storage.save(name, ContentFile(content))
        self.stats["files_copied"] += 1
        return saved

    def report(self):
        s = self.stats
        rows = [
            ("Категории", "categories", Category),
            ("Бренды", "brands", Brand),
            ("Товары", "products", Product),
            ("Варианты", "variants", ProductVariant),
            ("Фото товаров", "images", ProductImage),
            ("Отзывы", "reviews", Review),
            ("Промокоды", "promo", PromoCode),
        ]
        self.stdout.write(f"Каталог: {self.source}")
        for title, key, model in rows:
            self.stdout.write(
                f"  {title:<13} создано {s[f'{key}_created']:>3}, обновлено "
                f"{s[f'{key}_updated']:>3}, всего в БД {model.objects.count()}"
            )
        self.stdout.write(
            f"  Файлы         скопировано {s['files_copied']}, уже были {s['files_kept']}, "
            f"не найдено {s['images_missing']}"
        )
        self.stdout.write(f"  Демо-вход     {DEMO_EMAIL} / {DEMO_PASSWORD}")
        self.stdout.write(self.style.SUCCESS("Готово."))
