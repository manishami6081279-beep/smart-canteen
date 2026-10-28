from django.urls import path

from . import views

urlpatterns = [
    # public
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # menu (login required)
    path("menu/", views.menu, name="menu"),
    path("breakfast/", views.breakfast, name="breakfast"),
    path("lunch/", views.lunch, name="lunch"),
    path("snacks/", views.snacks, name="snacks"),
    path("beverages/", views.beverages, name="beverages"),
    path("desserts/", views.desserts, name="desserts"),
    path("todays-special/", views.todays_special, name="todays_special"),
    # cart / order / token
    path("cart/add/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:pk>/", views.remove_from_cart, name="remove_from_cart"),
    path("place-order/", views.place_order, name="place_order"),
    path("token/", views.token_latest, name="token"),
    path("token/<int:pk>/", views.token_detail, name="token_detail"),
    # feedback
    path("feedback/", views.feedback, name="feedback"),
]
