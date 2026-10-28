"""
Fills the database with the food items that were hard-coded in the original HTML pages.

Run:  python manage.py seed_menu
It is safe to run more than once - items that already exist are left unchanged.
"""
import shutil
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from canteen.models import FoodItem

# (name, category, diet, price, image file in static/images, is_popular)
MENU = [
    # Breakfast
    ("Idly", "breakfast", "", 30, "idly.png", True),
    ("Dosa", "breakfast", "", 50, "dosa.png", False),
    ("Pongal", "breakfast", "", 40, "pongal.png", False),
    ("Poori", "breakfast", "", 50, "poori.png", False),
    ("Vada", "breakfast", "", 10, "vada.png", False),
    # Lunch - veg
    ("Curd Rice", "lunch", "veg", 50, "curd.png", True),
    ("Sambar Rice", "lunch", "veg", 50, "sambar.png", False),
    ("Fried Rice", "lunch", "veg", 80, "fried.png", False),
    ("Veg Briyani", "lunch", "veg", 100, "veg.png", False),
    ("Lemon Rice", "lunch", "veg", 40, "lemon.png", False),
    # Lunch - non veg
    ("Chicken Briyani", "lunch", "nonveg", 110, "chicken.png", False),
    ("Mutton Briyani", "lunch", "nonveg", 150, "mutton.png", True),
    ("Parrota", "lunch", "nonveg", 30, "parrota.png", False),
    ("Chicken Rice", "lunch", "nonveg", 120, "crice.png", False),
    ("Chicken Noodles", "lunch", "nonveg", 110, "noodles.png", False),
    # Snacks
    ("Puffs", "snacks", "", 20, "puffs.png", False),
    ("Samosa", "snacks", "", 20, "samosa.png", False),
    ("Sandwich", "snacks", "", 60, "sand.png", False),
    ("Veg Roll", "snacks", "", 50, "veg_roll.png", False),
    ("Cookies", "snacks", "", 10, "cookies.png", False),
    # Beverages
    ("Tea", "beverages", "", 15, "tea.png", False),
    ("Coffee", "beverages", "", 20, "coffee.png", False),
    ("Fresh Juice", "beverages", "", 40, "juice.png", False),
    ("Rose Milk", "beverages", "", 40, "rose.png", False),
    ("Milk Shake", "beverages", "", 60, "milk.png", True),
    # Desserts
    ("Ice Cream", "dessert", "", 50, "ice.png", False),
    ("Brownie", "dessert", "", 50, "brownie.png", True),
    ("Honey Cake", "dessert", "", 30, "honey.png", False),
    ("Chocolate Cake", "dessert", "", 30, "cake.png", False),
    ("Pudding", "dessert", "", 40, "pudding.png", False),
    # Today's special
    ("Idiyappam", "special", "", 70, "idiyappan.png", False),
    ("Rava Kichadi", "special", "", 60, "ravakichadi.png", False),
    ("Mushroom", "special", "", 100, "mushroom.png", False),
    ("Kothu Parotta", "special", "", 80, "kothu.png", False),  # price was missing in the original page
    ("Mango", "special", "", 25, "mango.png", False),
    ("Badam Milk", "special", "", 30, "badam.png", False),
    ("Falooda", "special", "", 50, "falooda.png", False),
    ("Burger", "special", "", 70, "burger.png", False),
    ("Donut", "special", "", 40, "donut.png", False),
    ("French Fries", "special", "", 45, "french.png", False),
]


class Command(BaseCommand):
    help = "Load the canteen food menu (with images) into the database."

    def handle(self, *args, **options):
        source_dir = settings.BASE_DIR / "static" / "images"
        target_dir = settings.MEDIA_ROOT / "food"
        target_dir.mkdir(parents=True, exist_ok=True)

        created = skipped = 0
        order_counter = {}
        for name, category, diet, price, image_file, popular in MENU:
            source = source_dir / image_file
            if not source.exists():
                raise CommandError(f"Image not found: {source}")
            shutil.copyfile(source, target_dir / image_file)

            order_counter[category] = order_counter.get(category, 0) + 1
            # get_or_create: items that already exist (maybe edited in the admin) are left alone
            _, was_created = FoodItem.objects.get_or_create(
                name=name,
                category=category,
                defaults={
                    "diet": diet,
                    "price": Decimal(price),
                    "image": f"food/{image_file}",
                    "is_available": True,
                    "is_popular": popular,
                    "display_order": order_counter[category],
                },
            )
            created += was_created
            skipped += not was_created

        self.stdout.write(self.style.SUCCESS(
            f"Menu loaded: {created} items created, {skipped} already existed (left unchanged)."
        ))
