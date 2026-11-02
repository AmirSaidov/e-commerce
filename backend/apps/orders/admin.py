from django import forms
from django.contrib import admin, messages

from apps.core.exceptions import ApiException

from .models import Order, OrderItem
from .services import cancel_order

# Вручную — только движение заказа по складу. «Оплачен» ставит вебхук Stripe, отмена идёт через
# действие «Отменить», которое возвращает остатки на склад.
MANUAL_STATUSES = (Order.Status.ASSEMBLING, Order.Status.SHIPPED, Order.Status.DELIVERED)


class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ("status",)

    def clean_status(self):
        status = self.cleaned_data["status"]
        if status != self.instance.status and status not in MANUAL_STATUSES:
            raise forms.ValidationError(
                "Вручную можно поставить только «собирается», «передан в доставку» или "
                "«доставлен». Для отмены используйте действие «Отменить заказы»."
            )
        return status


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = ("product_name", "variant_name", "sku", "price", "quantity")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    form = OrderAdminForm
    list_display = (
        "number",
        "user",
        "status",
        "total",
        "delivery_method",
        "payment_method",
        "created_at",
    )
    list_filter = ("status", "delivery_method", "payment_method")
    search_fields = ("number", "user__email")
    readonly_fields = (
        "number",
        "user",
        "delivery_method",
        "payment_method",
        "address",
        "subtotal",
        "discount",
        "delivery_price",
        "total",
        "promo_code",
        "created_at",
        "paid_at",
        "cancelled_at",
    )
    inlines = (OrderItemInline,)
    actions = ("cancel_orders",)

    def has_add_permission(self, request):
        return False

    @admin.action(description="Отменить заказы (вернуть товары на склад)")
    def cancel_orders(self, request, queryset):
        for order in queryset:
            try:
                cancel_order(order)
            except ApiException as exc:
                self.message_user(request, f"{order.number}: {exc.detail}", messages.WARNING)
