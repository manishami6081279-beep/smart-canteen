from django.db.models import Sum

from .models import CartItem


def cart_summary(request):
    """Makes {{ cart_count }} available in every template (number of items in the cart)."""
    count = 0
    if request.user.is_authenticated:
        count = CartItem.objects.filter(user=request.user).aggregate(n=Sum("quantity"))["n"] or 0
    return {"cart_count": count}
