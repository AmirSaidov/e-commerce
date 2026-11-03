from django.contrib import admin

from .models import Cart, CartItem, PromoCode


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "type", "value", "expires_at", "is_active", "usage_limit")
    list_filter = ("type", "is_active")
    search_fields = ("code",)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    raw_id_fields = ("variant",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "updated_at")
    search_fields = ("user__email",)
    raw_id_fields = ("user",)
    inlines = (CartItemInline,)
