import re
from datetime import time

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import (
    DEPARTMENT_CHOICES,
    YEAR_CHOICES,
    ContactMessage,
    Feedback,
    Order,
    StudentProfile,
)

User = get_user_model()

NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,99}$")
UID_RE = re.compile(r"^[A-Za-z0-9]{4,20}$")
MOBILE_RE = re.compile(r"^[6-9]\d{9}$")


class RegistrationForm(forms.Form):
    name = forms.CharField(max_length=100, error_messages={"required": "Please enter your name."})
    uid_number = forms.CharField(max_length=20, error_messages={"required": "Please enter your UID number."})
    mobile = forms.CharField(max_length=10, error_messages={"required": "Please enter your mobile number."})
    year = forms.TypedChoiceField(
        choices=YEAR_CHOICES, coerce=int,
        error_messages={
            "required": "Please enter your year (1 to 4).",
            "invalid_choice": "Year must be between 1 and 4.",
        },
    )
    department = forms.ChoiceField(
        choices=DEPARTMENT_CHOICES,
        error_messages={
            "required": "Please select your department.",
            "invalid_choice": "Please select a valid department.",
        },
    )
    password = forms.CharField(strip=False, error_messages={"required": "Please choose a password."})
    confirm_password = forms.CharField(strip=False, error_messages={"required": "Please confirm your password."})

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        if not NAME_RE.match(name):
            raise ValidationError("Name can contain only letters, spaces and . ' - (minimum 2 characters).")
        return name

    def clean_uid_number(self):
        uid = self.cleaned_data["uid_number"].strip().upper()
        if not UID_RE.match(uid):
            raise ValidationError("UID must be 4 to 20 letters/digits with no spaces or symbols.")
        if StudentProfile.objects.filter(uid_number__iexact=uid).exists() or User.objects.filter(username__iexact=uid).exists():
            raise ValidationError("This UID is already registered. Please log in instead.")
        return uid

    def clean_mobile(self):
        mobile = self.cleaned_data["mobile"].strip().replace(" ", "")
        if not MOBILE_RE.match(mobile):
            raise ValidationError("Enter a valid 10-digit mobile number (it must start with 6, 7, 8 or 9).")
        return mobile

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        confirm = cleaned.get("confirm_password")
        if password and confirm and password != confirm:
            self.add_error("confirm_password", "The two passwords do not match.")
        elif password:
            try:
                validate_password(password)
            except ValidationError as exc:
                self.add_error("password", exc)
        return cleaned

    def save(self):
        """Create the User (hashed password) and the StudentProfile together."""
        data = self.cleaned_data
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=data["uid_number"],
                    password=data["password"],  # create_user hashes it
                    first_name=data["name"][:150],
                )
                StudentProfile.objects.create(
                    user=user,
                    name=data["name"],
                    uid_number=data["uid_number"],
                    mobile=data["mobile"],
                    year=data["year"],
                    department=data["department"],
                )
        except IntegrityError:
            # Two people submitting the same UID at the same moment
            self.add_error("uid_number", "This UID is already registered. Please log in instead.")
            return None
        return user


class LoginForm(forms.Form):
    uid_number = forms.CharField(max_length=20, error_messages={"required": "Please enter your UID number."})
    password = forms.CharField(strip=False, error_messages={"required": "Please enter your password."})

    def clean_uid_number(self):
        return self.cleaned_data["uid_number"].strip().upper()


class OrderForm(forms.Form):
    name = forms.CharField(max_length=100, error_messages={"required": "Please enter your name."})
    department = forms.ChoiceField(
        choices=DEPARTMENT_CHOICES,
        error_messages={"required": "Please select your department.", "invalid_choice": "Invalid department."},
    )
    pickup_time = forms.TimeField(error_messages={"required": "Please choose a pick-up time.", "invalid": "Enter a valid time."})
    pickup_date = forms.DateField(error_messages={"required": "Please choose a date.", "invalid": "Enter a valid date."})
    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_CHOICES,
        error_messages={"required": "Please choose a payment method.", "invalid_choice": "Invalid payment method."},
    )

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        if len(name) < 2:
            raise ValidationError("Please enter your full name.")
        return name

    def clean(self):
        cleaned = super().clean()
        pickup_date = cleaned.get("pickup_date")
        pickup_time = cleaned.get("pickup_time")
        if not pickup_date or not pickup_time:
            return cleaned

        now = timezone.localtime()
        if pickup_date < now.date():
            self.add_error("pickup_date", "Pick-up date cannot be in the past.")
            return cleaned

        opening = time(settings.CANTEEN_OPEN_HOUR, 0)
        closing = time(settings.CANTEEN_CLOSE_HOUR, 0)
        if not (opening <= pickup_time <= closing):
            self.add_error(
                "pickup_time",
                f"The canteen is open {opening.strftime('%I:%M %p')} to {closing.strftime('%I:%M %p')}. Please pick a time in that range.",
            )
        elif pickup_date == now.date() and pickup_time <= now.time().replace(second=0, microsecond=0):
            self.add_error("pickup_time", "Pick-up time must be later than the current time.")
        return cleaned


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["name", "token_number", "rating", "taste", "quantity", "hygiene", "comments"]
        error_messages = {
            "name": {"required": "Please enter your name."},
            "rating": {
                "required": "Please rate our service.",
                "invalid_choice": "Please choose one of the ratings.",
            },
            "token_number": {"invalid": "Enter your token number as a number, e.g. 7."},
        }

    def clean_name(self):
        return " ".join(self.cleaned_data["name"].split())


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "message"]
        error_messages = {
            "name": {"required": "Please enter your name."},
            "email": {"required": "Please enter your email.", "invalid": "Please enter a valid email address."},
            "message": {"required": "Please write a message."},
        }
