import factory

from apps.users.models import User

PASSWORD = "Volt-Str0ng-pass"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@voltra.kz")
    first_name = "Айбек"
    last_name = "Сапаров"
    is_email_verified = True
    password = PASSWORD

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class.objects.create_user(*args, **kwargs)
