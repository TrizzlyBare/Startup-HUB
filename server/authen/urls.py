from django.urls import path
from .views import login, register, test_token

urlpatterns = [
    path("login/", login, name="login"),
    path("register/", register, name="register"),
    path("test-token/", test_token, name="test_token"),
]
