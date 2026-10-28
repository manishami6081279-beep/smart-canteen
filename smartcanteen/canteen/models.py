from decimal import Decimal

from django.conf import settings
from django.db import models

DEPARTMENT_CHOICES = [
    ("CSE", "CSE"),
    ("AI&DS", "AI&DS"),
    ("IT", "IT"),
    ("EEE", "EEE"),
    ("MECH", "MECH"),
    ("ECE", "ECE"),
    ("CIVIL", "CIVIL"),
]

YEAR_CHOICES = [(1, "1"), (2, "2"), (3, "3"), (4, "4")]


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------
class StudentProfile(models.Model):
    """
    Extra details for a student. Django's built-in User model stores the login
    (username = UID number, hashed password); this table stores everything else.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    name = models.CharField(max_length=100)
    uid_number = models.CharField(max_length=20, unique=True)
    mobile = models.CharField(max_length=10)
    year = models.PositiveSmallIntegerField(choices=YEAR_CHOICES)
    department = models.CharField(max_length=10, choices=DEPARTMENT_CHOICES)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-registered_at"]

    def __str__(self):
        return f"{self.name} ({self.uid_number})"


# ---------------------------------------------------------------------------
# Food menu
# ---------------------------------------------------------------------------
class FoodItem(models.Model):
    CATEGORY_CHOICES = [
        ("breakfast", "Breakfast"),
        ("lunch", "Lunch"),
        ("snacks", "Snacks"),
        ("beverages", "Beverages"),
        ("dessert", "Desserts"),
        ("special", "Today's Special"),
    ]
    DIET_CHOICES = [
        ("", "Not applicable"),
        ("veg", "Veg"),
        ("nonveg", "Non-Veg"),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    diet = models.CharField(
        max_length=10, choices=DIET_CHOICES, blank=True, default="",
        help_text="Used on the Lunch page to split VEG / NON VEG.",
    )
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to="food/", blank=True)
    is_available = models.BooleanField(default=True)
    is_popular = models.BooleanField(
        default=False, help_text="Show on the home page under POPULAR ITEMS."
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["category", "display_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "category"], name="unique_food_per_category"),
        ]

    def __str__(self):
        return f"{self.name} - ₹{self.price}"


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------
class CartItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart_items"
    )
    food = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "food"], name="one_cart_row_per_food"),
        ]

    @property
    def subtotal(self):
        return self.food.price * self.quantity

    def __str__(self):
        return f"{self.user} - {self.food.name} x {self.quantity}"


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
class Order(models.Model):
    PAYMENT_CHOICES = [("Cash", "Cash"), ("UPI", "UPI"), ("Card", "Card")]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("preparing", "Preparing"),
        ("ready", "Ready for pickup"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders"
    )
    # A token restarts from 1 every day: TKN001, TKN002, ...
    token_date = models.DateField()
    token_number = models.PositiveIntegerField()

    customer_name = models.CharField(max_length=100)
    department = models.CharField(max_length=10, choices=DEPARTMENT_CHOICES)
    pickup_date = models.DateField()
    pickup_time = models.TimeField()
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["token_date", "token_number"], name="unique_token_per_day"
            ),
        ]

    @property
    def token_label(self):
        return f"TKN{self.token_number:03d}"

    def __str__(self):
        return f"{self.token_label} ({self.token_date}) - {self.customer_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    food = models.ForeignKey(FoodItem, on_delete=models.SET_NULL, null=True, blank=True)
    # Name and price are copied so old orders stay correct if the menu changes later.
    item_name = models.CharField(max_length=100)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField()

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.item_name} x {self.quantity}"


# ---------------------------------------------------------------------------
# Feedback and contact messages
# ---------------------------------------------------------------------------
class Feedback(models.Model):
    RATING_CHOICES = [
        ("excellent", "Excellent"),
        ("good", "Good"),
        ("average", "Average"),
        ("poor", "Poor"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feedbacks"
    )
    name = models.CharField(max_length=100)
    token_number = models.PositiveIntegerField(null=True, blank=True)
    rating = models.CharField(max_length=10, choices=RATING_CHOICES)
    taste = models.BooleanField(default=False)
    quantity = models.BooleanField(default=False)
    hygiene = models.BooleanField(default=False)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.rating}"


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} <{self.email}>"
