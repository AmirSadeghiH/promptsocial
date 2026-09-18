from django.contrib.auth import authenticate, get_user_model, login, logout
from django.shortcuts import redirect, render


def login_page(request):
    if request.user.is_authenticated:
        return redirect("web:home")

    error = None
    if request.method == "POST":
        identifier = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        User = get_user_model()
        found = User.objects.filter(
            username__iexact=identifier
        ).first() or User.objects.filter(email__iexact=identifier).first()
        user = authenticate(request, username=found.username, password=password) if found else None
        if user:
            login(request, user)
            return redirect("web:home")
        error = "Invalid username or password."

    return render(request, "web/login.html", {"error": error})


def signup_page(request):
    if request.user.is_authenticated:
        return redirect("web:home")

    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        User = get_user_model()

        if len(password) < 8:
            error = "Password must be at least 8 characters."
        elif User.objects.filter(username__iexact=username).exists():
            error = "This username is already taken."
        elif User.objects.filter(email__iexact=email).exists():
            error = "This email is already registered."
        else:
            user = User.objects.create_user(
                username=username, email=email, password=password, display_name=username
            )
            login(request, user)
            return redirect("web:home")

    return render(request, "web/signup.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("web:home")
