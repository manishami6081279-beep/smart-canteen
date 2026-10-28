import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Max, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import ContactForm, FeedbackForm, LoginForm, OrderForm, RegistrationForm
from .models import CartItem, FoodItem, Order, OrderItem

MAX_QTY_PER_ITEM = 20


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------
def home(request):
    popular = FoodItem.objects.filter(is_popular=True, is_available=True).order_by("display_order", "name")
    return render(request, "canteen/homepage.html", {"popular_items": popular})


def about(request):
    return render(request, "canteen/about.html")


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your message has been sent successfully!")
            return redirect("contact")
        messages.error(request, "Please correct the errors below.")
    else:
        initial = {}
        if request.user.is_authenticated:
            initial["name"] = request.user.first_name
        form = ContactForm(initial=initial)
    return render(request, "canteen/contact.html", {"form": form})


# ---------------------------------------------------------------------------
# Registration, login, logout
# ---------------------------------------------------------------------------
def register(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            if user is not None:
                messages.success(request, "Registration successful! Please log in with your UID number and password.")
                return redirect("login")
        messages.error(request, "Registration failed. Please correct the errors below.")
    else:
        form = RegistrationForm()
    return render(request, "canteen/canreg.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    next_url = request.POST.get("next") or request.GET.get("next") or ""

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data["uid_number"],
                password=form.cleaned_data["password"],
            )
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome, {user.first_name or user.username}!")
                if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                    return redirect(next_url)
                return redirect("home")
            messages.error(request, "Invalid UID number or password. Please try again.")
        else:
            messages.error(request, "Please enter both your UID number and password.")
    else:
        form = LoginForm()
    return render(request, "canteen/canteenlogin.html", {"form": form, "next": next_url})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("login")


# ---------------------------------------------------------------------------
# Menu pages (login required)
# ---------------------------------------------------------------------------
def _items(category, diet=None):
    qs = FoodItem.objects.filter(category=category)
    if diet:
        qs = qs.filter(diet=diet)
    return qs.order_by("display_order", "name")


@login_required
def menu(request):
    q = request.GET.get("q", "").strip()

    def section(category, diet=None):
        qs = _items(category, diet)
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    context = {
        "q": q,
        "breakfast": section("breakfast"),
        "lunch_veg": section("lunch", "veg"),
        "lunch_nonveg": section("lunch", "nonveg"),
        "snacks": section("snacks"),
        "beverages": section("beverages"),
        "desserts": section("dessert"),
    }
    context["nothing_found"] = bool(q) and not any(
        context[k].exists() for k in ("breakfast", "lunch_veg", "lunch_nonveg", "snacks", "beverages", "desserts")
    )
    return render(request, "canteen/menu.html", context)


@login_required
def breakfast(request):
    return render(request, "canteen/breakefast.html", {"items": _items("breakfast")})


@login_required
def lunch(request):
    return render(
        request,
        "canteen/lunch.html",
        {"veg_items": _items("lunch", "veg"), "nonveg_items": _items("lunch", "nonveg")},
    )


@login_required
def snacks(request):
    return render(request, "canteen/snacks.html", {"items": _items("snacks")})


@login_required
def beverages(request):
    return render(request, "canteen/beverages.html", {"items": _items("beverages")})


@login_required
def desserts(request):
    return render(request, "canteen/dessert.html", {"items": _items("dessert")})


@login_required
def todays_special(request):
    return render(request, "canteen/todayspecial.html", {"items": _items("special")})


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------
def _cart_count(user):
    return CartItem.objects.filter(user=user).aggregate(n=Sum("quantity"))["n"] or 0


@require_POST
def add_to_cart(request):
    """Called by static/js/canteen.js when "Add to cart" is clicked. Returns JSON."""
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "login_required": True, "message": "Please log in first."}, status=401)

    try:
        payload = json.loads(request.body or "{}")
        item_id = int(payload.get("item_id"))
        qty = int(payload.get("quantity", 1))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "message": "Invalid request."}, status=400)

    if qty < 1 or qty > MAX_QTY_PER_ITEM:
        return JsonResponse({"ok": False, "message": f"Quantity must be between 1 and {MAX_QTY_PER_ITEM}."}, status=400)

    food = FoodItem.objects.filter(pk=item_id).first()
    if food is None:
        return JsonResponse({"ok": False, "message": "This item does not exist."}, status=404)
    if not food.is_available:
        return JsonResponse({"ok": False, "message": f"Sorry, {food.name} is currently unavailable."}, status=400)

    # Same behaviour as the original page: adding again replaces the quantity.
    CartItem.objects.update_or_create(user=request.user, food=food, defaults={"quantity": qty})
    return JsonResponse(
        {"ok": True, "message": f"{food.name} added to cart", "cart_count": _cart_count(request.user)}
    )


@login_required
@require_POST
def remove_from_cart(request, pk):
    deleted, _ = CartItem.objects.filter(pk=pk, user=request.user).delete()
    if deleted:
        messages.info(request, "Item removed from your cart.")
    return redirect("place_order")


# ---------------------------------------------------------------------------
# Place order / token
# ---------------------------------------------------------------------------
def _create_order(user, data, cart_items):
    """Create the order, its items and a daily token number, then empty the cart."""
    for _attempt in range(5):
        try:
            with transaction.atomic():
                today = timezone.localdate()
                last = Order.objects.filter(token_date=today).aggregate(m=Max("token_number"))["m"] or 0
                total = sum((ci.food.price * ci.quantity for ci in cart_items), Decimal("0"))
                order = Order.objects.create(
                    user=user,
                    token_date=today,
                    token_number=last + 1,
                    customer_name=data["name"],
                    department=data["department"],
                    pickup_date=data["pickup_date"],
                    pickup_time=data["pickup_time"],
                    payment_method=data["payment_method"],
                    total_amount=total,
                )
                OrderItem.objects.bulk_create(
                    [
                        OrderItem(order=order, food=ci.food, item_name=ci.food.name,
                                  unit_price=ci.food.price, quantity=ci.quantity)
                        for ci in cart_items
                    ]
                )
                CartItem.objects.filter(user=user).delete()
            return order
        except IntegrityError:
            continue  # another student took this token number at the same moment - try the next one
    raise RuntimeError("Could not generate a token number. Please try again.")


@login_required
def place_order(request):
    cart_items = list(CartItem.objects.filter(user=request.user).select_related("food"))
    if not cart_items:
        messages.warning(request, "Your cart is empty. Please add some items from the menu first.")
        return redirect("menu")

    total = sum((ci.subtotal for ci in cart_items), Decimal("0"))
    now = timezone.localtime()

    if request.method == "POST":
        form = OrderForm(request.POST)
        unavailable = [ci.food.name for ci in cart_items if not ci.food.is_available]
        if unavailable:
            messages.error(request, "These items are no longer available: " + ", ".join(unavailable) + ". Please remove them.")
        elif form.is_valid():
            try:
                order = _create_order(request.user, form.cleaned_data, cart_items)
            except RuntimeError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, "Order placed successfully!")
                return redirect("token_detail", pk=order.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        profile = getattr(request.user, "profile", None)
        form = OrderForm(initial={
            "name": request.user.first_name,
            "department": profile.department if profile else "",
            "pickup_date": now.date().isoformat(),
        })

    return render(request, "canteen/placeorder.html", {
        "form": form,
        "cart_items": cart_items,
        "total": total,
        "today": now.date().isoformat(),
    })


@login_required
def token_latest(request):
    order = Order.objects.filter(user=request.user).first()  # newest first (Meta.ordering)
    if order is None:
        messages.info(request, "You have not placed any order yet.")
        return redirect("menu")
    return redirect("token_detail", pk=order.pk)


@login_required
def token_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, "canteen/token.html", {"order": order})


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------
@login_required
def feedback(request):
    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, "Thank you for your feedback! 😊")
            return redirect("home")
        messages.error(request, "Please correct the errors below.")
    else:
        initial = {"name": request.user.first_name}
        token = request.GET.get("token", "")
        if token.isdigit():
            initial["token_number"] = int(token)
        form = FeedbackForm(initial=initial)
    return render(request, "canteen/feedback.html", {"form": form})
