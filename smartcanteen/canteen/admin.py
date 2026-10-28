from django.contrib import admin

from .models import CartItem, ContactMessage, Feedback, FoodItem, Order, OrderItem, StudentProfile

admin.site.site_header = "Smart Canteen Admin"
admin.site.site_title = "Smart Canteen"


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "uid_number", "mobile", "year", "department", "registered_at")
    list_filter = ("department", "year")
    search_fields = ("name", "uid_number", "mobile")
    readonly_fields = ("registered_at",)


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "diet", "price", "is_available", "is_popular", "display_order")
    list_editable = ("price", "is_available", "is_popular", "display_order")
    list_filter = ("category", "diet", "is_available", "is_popular")
    search_fields = ("name",)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("user", "food", "quantity", "added_at")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("food", "item_name", "unit_price", "quantity")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("token_label", "token_date", "customer_name", "department", "pickup_date",
                    "pickup_time", "payment_method", "total_amount", "status")
    list_editable = ("status",)
    list_filter = ("status", "token_date", "payment_method", "department")
    search_fields = ("customer_name", "user__username")
    inlines = [OrderItemInline]
    readonly_fields = ("created_at",)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("name", "token_number", "rating", "taste", "quantity", "hygiene", "created_at")
    list_filter = ("rating",)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created_at")
    search_fields = ("name", "email", "message")
