import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (CartItem, ContactMessage, Feedback, FoodItem, Order,
                     OrderItem, StudentProfile)

User = get_user_model()

REG = {
    "name": "Kiruthika S",
    "uid_number": "21cs101",
    "mobile": "9025751236",
    "year": "3",
    "department": "CSE",
    "password": "Canteen@123",
    "confirm_password": "Canteen@123",
}


def make_student(uid="21CS101", password="Canteen@123"):
    user = User.objects.create_user(username=uid, password=password, first_name="Test Student")
    StudentProfile.objects.create(user=user, name="Test Student", uid_number=uid,
                                  mobile="9025751236", year=2, department="IT")
    return user


class SeedTests(TestCase):
    def test_seed_is_repeatable(self):
        call_command("seed_menu", verbosity=0)
        first = FoodItem.objects.count()
        call_command("seed_menu", verbosity=0)
        self.assertEqual(first, 40)
        self.assertEqual(FoodItem.objects.count(), 40)
        self.assertEqual(FoodItem.objects.filter(is_popular=True).count(), 5)


class RegistrationTests(TestCase):
    def test_page_loads(self):
        r = self.client.get(reverse("register"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "REGISTRATION FORM")

    def test_successful_registration(self):
        r = self.client.post(reverse("register"), REG, follow=True)
        self.assertRedirects(r, reverse("login"))
        self.assertContains(r, "Registration successful")
        profile = StudentProfile.objects.get(uid_number="21CS101")
        self.assertEqual(profile.name, "Kiruthika S")
        self.assertEqual(profile.department, "CSE")
        self.assertIsNotNone(profile.registered_at)
        # password is hashed, never plain text
        self.assertNotEqual(profile.user.password, REG["password"])
        self.assertTrue(profile.user.password.startswith("pbkdf2_"))

    def test_duplicate_uid_rejected_case_insensitive(self):
        self.client.post(reverse("register"), REG)
        r = self.client.post(reverse("register"), {**REG, "uid_number": "21CS101", "name": "Someone Else"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "already registered")
        self.assertEqual(StudentProfile.objects.count(), 1)

    def test_validation_errors(self):
        r = self.client.post(reverse("register"), {
            "name": "", "uid_number": "a b", "mobile": "12345", "year": "9",
            "department": "XYZ", "password": "abc", "confirm_password": "abd"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(StudentProfile.objects.count(), 0)
        form = r.context["form"]
        for field in ("name", "uid_number", "mobile", "year", "department"):
            self.assertIn(field, form.errors, field)
        self.assertIn("confirm_password", form.errors)

    def test_password_rules(self):
        r = self.client.post(reverse("register"), {**REG, "password": "abc", "confirm_password": "abc"})
        self.assertIn("password", r.context["form"].errors)
        self.assertEqual(User.objects.count(), 0)


class LoginTests(TestCase):
    def setUp(self):
        self.user = make_student()

    def test_login_success_redirects_home(self):
        r = self.client.post(reverse("login"), {"uid_number": "21cs101", "password": "Canteen@123"}, follow=True)
        self.assertRedirects(r, reverse("home"))
        self.assertContains(r, "Welcome, Test Student")
        self.assertContains(r, "LOGOUT")
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_wrong_password(self):
        r = self.client.post(reverse("login"), {"uid_number": "21CS101", "password": "wrong"})
        self.assertContains(r, "Invalid UID number or password")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_unknown_user(self):
        r = self.client.post(reverse("login"), {"uid_number": "NOPE", "password": "x"})
        self.assertContains(r, "Invalid UID number or password")

    def test_logout_requires_post_and_works(self):
        self.client.login(username="21CS101", password="Canteen@123")
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        r = self.client.post(reverse("logout"), follow=True)
        self.assertRedirects(r, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_protected_pages_redirect_to_login(self):
        for name in ("menu", "breakfast", "lunch", "snacks", "beverages", "desserts",
                     "todays_special", "place_order", "token", "feedback"):
            url = reverse(name)
            r = self.client.get(url)
            self.assertRedirects(r, f"{reverse('login')}?next={url}", fetch_redirect_response=False, msg_prefix=name)

    def test_public_pages_open(self):
        for name in ("home", "about", "contact", "register", "login"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_next_redirect_and_open_redirect_blocked(self):
        r = self.client.post(reverse("login"), {"uid_number": "21CS101", "password": "Canteen@123",
                                                "next": reverse("menu")})
        self.assertRedirects(r, reverse("menu"), fetch_redirect_response=False)
        self.client.post(reverse("logout"))
        r = self.client.post(reverse("login"), {"uid_number": "21CS101", "password": "Canteen@123",
                                                "next": "https://evil.example.com/"})
        self.assertRedirects(r, reverse("home"), fetch_redirect_response=False)


class MenuAndCartTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_menu", verbosity=0)

    def setUp(self):
        self.user = make_student()
        self.client.login(username="21CS101", password="Canteen@123")

    def test_pages_show_database_items(self):
        expectations = {
            "menu": ["IDLY", "MUTTON BRIYANI", "PUFFS", "TEA", "BROWNIE"],
            "breakfast": ["Idly-30", "Vada-10"],
            "lunch": ["CURD RICE", "CHICKEN NOODLES", "NON VEG"],
            "snacks": ["SAMOSA", "COOKIES"],
            "beverages": ["ROSE MILK", "MILK SHAKE"],
            "desserts": ["PUDDING", "HONEY CAKE"],
            "todays_special": ["Idiyappam - ₹70", "Falooda - ₹50", "French Fries - ₹45"],
        }
        for name, texts in expectations.items():
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 200, name)
            for t in texts:
                self.assertContains(r, t, msg_prefix=name)
            self.assertContains(r, "/media/food/", msg_prefix=name)

    def test_homepage_popular_items(self):
        r = self.client.get(reverse("home"))
        for t in ("Idly-30", "Curd Rice-50", "Mutton Briyani-150", "Milk Shake-60", "Brownie-50"):
            self.assertContains(r, t)

    def test_price_change_in_db_reflected(self):
        FoodItem.objects.filter(name="Tea").update(price=17)
        self.assertContains(self.client.get(reverse("beverages")), "price:₹17")

    def test_unavailable_item_is_disabled(self):
        FoodItem.objects.filter(name="Tea").update(is_available=False)
        r = self.client.get(reverse("beverages"))
        self.assertContains(r, "Currently unavailable")
        tea = FoodItem.objects.get(name="Tea")
        resp = self._add(tea.id, 1)
        self.assertEqual(resp.status_code, 400)

    def test_search(self):
        r = self.client.get(reverse("menu"), {"q": "briyani"})
        self.assertContains(r, "MUTTON BRIYANI")
        self.assertNotContains(r, "PUFFS")
        r = self.client.get(reverse("menu"), {"q": "zzzz"})
        self.assertContains(r, "no food item matches")

    def _add(self, item_id, qty):
        return self.client.post(reverse("add_to_cart"), data=json.dumps({"item_id": item_id, "quantity": qty}),
                                content_type="application/json")

    def test_add_to_cart_and_replace_quantity(self):
        idly = FoodItem.objects.get(name="Idly")
        r = self._add(idly.id, 2)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["cart_count"], 2)
        r = self._add(idly.id, 3)  # same behaviour as the original page: quantity replaced
        self.assertEqual(r.json()["cart_count"], 3)
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 1)

    def test_add_to_cart_validation(self):
        idly = FoodItem.objects.get(name="Idly")
        self.assertEqual(self._add(idly.id, 0).status_code, 400)
        self.assertEqual(self._add(idly.id, 999).status_code, 400)
        self.assertEqual(self._add(99999, 1).status_code, 404)
        r = self.client.post(reverse("add_to_cart"), data="not json", content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_add_to_cart_anonymous_gets_401(self):
        self.client.logout()
        r = self._add(1, 1)
        self.assertEqual(r.status_code, 401)
        self.assertTrue(r.json()["login_required"])

    def test_cart_is_per_user(self):
        idly = FoodItem.objects.get(name="Idly")
        self._add(idly.id, 2)
        other = make_student("22IT202")
        self.client.logout()
        self.client.login(username="22IT202", password="Canteen@123")
        self.assertEqual(CartItem.objects.filter(user=other).count(), 0)
        self.assertRedirects(self.client.get(reverse("place_order")), reverse("menu"), fetch_redirect_response=False)

    def test_remove_from_cart(self):
        idly = FoodItem.objects.get(name="Idly")
        self._add(idly.id, 2)
        ci = CartItem.objects.get()
        # someone else cannot delete it
        make_student("22IT202")
        c2 = self.client_class()
        c2.login(username="22IT202", password="Canteen@123")
        c2.post(reverse("remove_from_cart", args=[ci.pk]))
        self.assertEqual(CartItem.objects.count(), 1)
        self.client.post(reverse("remove_from_cart", args=[ci.pk]))
        self.assertEqual(CartItem.objects.count(), 0)


class OrderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_menu", verbosity=0)

    def setUp(self):
        self.user = make_student()
        self.client.login(username="21CS101", password="Canteen@123")
        idly = FoodItem.objects.get(name="Idly")
        dosa = FoodItem.objects.get(name="Dosa")
        CartItem.objects.create(user=self.user, food=idly, quantity=2)
        CartItem.objects.create(user=self.user, food=dosa, quantity=1)

    def payload(self, **over):
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()
        data = {"name": "Test Student", "department": "IT", "pickup_time": "12:30",
                "pickup_date": tomorrow, "payment_method": "UPI"}
        data.update(over)
        return data

    def test_order_page_shows_cart_and_total(self):
        r = self.client.get(reverse("place_order"))
        self.assertContains(r, "Idly")
        self.assertContains(r, "₹110")  # 2*30 + 50, same as the original sample
        self.assertEqual(r.context["form"].initial["department"], "IT")

    def test_place_order_creates_everything_and_empties_cart(self):
        r = self.client.post(reverse("place_order"), self.payload())
        order = Order.objects.get()
        self.assertRedirects(r, reverse("token_detail", args=[order.pk]))
        self.assertEqual(order.token_label, "TKN001")
        self.assertEqual(order.total_amount, 110)
        self.assertEqual(OrderItem.objects.filter(order=order).count(), 2)
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 0)
        page = self.client.get(reverse("token_detail", args=[order.pk]))
        self.assertContains(page, "TKN001")
        self.assertContains(page, "Pending")

    def test_price_is_taken_from_server_not_browser(self):
        self.client.post(reverse("place_order"), self.payload(total="1", price="1"))
        self.assertEqual(Order.objects.get().total_amount, 110)

    def test_token_numbers_increase_per_day(self):
        self.client.post(reverse("place_order"), self.payload())
        CartItem.objects.create(user=self.user, food=FoodItem.objects.get(name="Tea"), quantity=1)
        self.client.post(reverse("place_order"), self.payload())
        self.assertEqual(list(Order.objects.order_by("token_number").values_list("token_number", flat=True)), [1, 2])

    def test_price_snapshot_survives_menu_change(self):
        self.client.post(reverse("place_order"), self.payload())
        FoodItem.objects.filter(name="Idly").update(price=99)
        self.assertEqual(Order.objects.get().total_amount, 110)
        self.assertEqual(OrderItem.objects.get(item_name="Idly").unit_price, 30)

    def test_validation(self):
        yesterday = (timezone.localdate() - timedelta(days=1)).isoformat()
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()
        cases = [
            (self.payload(pickup_date=yesterday), "pickup_date"),
            (self.payload(pickup_time="03:00"), "pickup_time"),
            (self.payload(pickup_time="23:00"), "pickup_time"),
            (self.payload(payment_method="Bitcoin"), "payment_method"),
            (self.payload(department="XYZ"), "department"),
            (self.payload(name=""), "name"),
            (self.payload(pickup_date=""), "pickup_date"),
        ]
        for data, field in cases:
            r = self.client.post(reverse("place_order"), data)
            self.assertEqual(r.status_code, 200, field)
            self.assertIn(field, r.context["form"].errors, field)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 2)

    def test_cannot_order_unavailable_item(self):
        FoodItem.objects.filter(name="Dosa").update(is_available=False)
        r = self.client.post(reverse("place_order"), self.payload())
        self.assertContains(r, "no longer available")
        self.assertEqual(Order.objects.count(), 0)

    def test_cannot_view_other_students_token(self):
        self.client.post(reverse("place_order"), self.payload())
        order = Order.objects.get()
        make_student("22IT202")
        c2 = self.client_class()
        c2.login(username="22IT202", password="Canteen@123")
        self.assertEqual(c2.get(reverse("token_detail", args=[order.pk])).status_code, 404)

    def test_token_latest_redirect(self):
        self.client.post(reverse("place_order"), self.payload())
        order = Order.objects.get()
        self.assertRedirects(self.client.get(reverse("token")), reverse("token_detail", args=[order.pk]))


class FeedbackContactTests(TestCase):
    def setUp(self):
        self.user = make_student()

    def test_feedback_saved(self):
        self.client.login(username="21CS101", password="Canteen@123")
        r = self.client.get(reverse("feedback"), {"token": "7"})
        self.assertContains(r, 'value="7"')
        r = self.client.post(reverse("feedback"), {"name": "Test Student", "token_number": "7",
                                                   "rating": "good", "taste": "on", "hygiene": "on",
                                                   "comments": "Nice"}, follow=True)
        self.assertRedirects(r, reverse("home"))
        fb = Feedback.objects.get()
        self.assertEqual((fb.rating, fb.taste, fb.quantity, fb.hygiene, fb.token_number), ("good", True, False, True, 7))

    def test_feedback_requires_rating(self):
        self.client.login(username="21CS101", password="Canteen@123")
        r = self.client.post(reverse("feedback"), {"name": "X"})
        self.assertIn("rating", r.context["form"].errors)
        self.assertEqual(Feedback.objects.count(), 0)

    def test_contact_saved_for_anyone(self):
        r = self.client.post(reverse("contact"), {"name": "A", "email": "a@b.com", "message": "Hi"}, follow=True)
        self.assertContains(r, "sent successfully")
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_contact_validation(self):
        r = self.client.post(reverse("contact"), {"name": "A", "email": "bad", "message": ""})
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertIn("email", r.context["form"].errors)
