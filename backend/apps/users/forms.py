from django.contrib.auth import forms as auth_forms

from .models import User


class UserCreationForm(auth_forms.UserCreationForm):
    class Meta:
        model = User
        fields = ("email",)


class UserChangeForm(auth_forms.UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"
