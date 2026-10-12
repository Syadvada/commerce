from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from decimal import Decimal


from .models import User, Category, Listing, Bid, Comment

# Create your views here.

# Create index view to display all active listings
def index(request):
    listings = Listing.objects.filter(is_active=True)
    for listing in listings:
        bid = highest_bid(listing)
        if bid:
            listing.current_bid = bid.amount
        else:
            listing.current_bid = listing.starting_bid

    return render(request, "auctions/index.html", {
        "listings": listings
    })

# Create login view to handle user authentication
def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)


        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


# Create logout view to handle user logout
def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


# Create register view to handle user registration
def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")


# Create highest_bid view to display the highest bid for a listing
def highest_bid(listing):
    return listing.bids.order_by('-amount').first()


# Create listing_detail to display individual listing's detail
def listing_detail(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)
    bids = listing.bids.order_by('amount')
    highest = highest_bid(listing)
    if highest:
        current_bid = highest.amount
    else:
        current_bid = listing.starting_bid

    return render(request, "auctions/listing.html", {
        "listing": listing,
        "bids": bids,
        "current_bid": current_bid,
        "highest_bid": highest,
        "comments": listing.comments.all()
    })


# Create new listing
@login_required
def create_listing(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        starting_bid = request.POST.get("starting_bid")
        image_url = request.POST.get("image_url")
        category_id = request.POST.get("category")

        if not title or not description or not starting_bid or not category_id:
            return render(request, "auctions/create.html", {
                "error": "All required fields must be completed.",
                "categories": Category.objects.all()
            })

        try:
            starting_bid = Decimal(starting_bid)
        except InvalidOperation:
            return render(request, "auctions/create.html", {
                "error": "Starting bid must be a valid number.",
                "categories": Category.objects.all()
            })

        if starting_bid < 0:
            return render(request, "auctions/create.html", {
                "error": "Starting bid cannot be negative.",
                "categories": Category.objects.all()
            })

        category = get_object_or_404(Category, id=category_id)

        listing = Listing.objects.create(owner=request.user, title=title, description=description, starting_bid=starting_bid, image_url=image_url, category=category)

        return redirect("listing_detail", listing_id=listing.id)

    return render(request, "auctions/create.html", {
        "categories": Category.objects.all()
    })


# Create a function to close a listing
@login_required
def close_listing(request, listing_id):
    if request.method != "POST":
        return redirect("listing_detail", listing_id=listing_id)
    
    listing = get_object_or_404(Listing, id=listing_id)

    if listing.owner != request.user:
        messages.error(request, "Only the owner is able to close the listing.")
        return redirect("listing_detail", listing_id=listing_id)

    if not listing.is_active:
        messages.error(request, "Invalid action. The listing is already closed.")
        return redirect("listing_detail", listing_id=listing_id)

    listing.is_active = False
    listing.save()

    return redirect("listing_detail", listing_id=listing_id)


# Add/remove a user from the watchers list for a listing
def toggle_watchlist(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)

    if request.user in listing.watchers.all():
        listing.watchers.remove(request.user)
        messages.success(request, "Listing removed from your watchlist.")
    else:
        listing.watchers.add(request.user)
        messages.success(request, "Listing added to your watchlist.")

    return redirect("listing_detail", listing_id=listing.id)


# Create watchlist from all the listings a user watch
@login_required
def watchlist(request):
    listings = request.user.watchlist.all()

    for listing in listings:
        bid = highest_bid(listing)
        if bid is not None:
            listing.current_bid = bid.amount
        else:
            listing.current_bid = listing.starting_bid

    return render(request, "auctions/watchlist.html", {
        "listings": listings
    })


# Create a bid for a listing
@login_required
def place_bid(request, listing_id):
    if request.method != "POST":
        return redirect("listing_detail", listing_id=listing_id)

    listing = get_object_or_404(Listing, id=listing_id)

    if not listing.is_active:
        messages.error(request, "You cannot bid on closed listing.")
        return redirect("listing_detail", listing_id=listing_id)

    if listing.owner == request.user:
        messages.error(request, "You are not allowed to bid your own listing.")
        return redirect("listing_detail", listing_id=listing_id)

    amount = request.POST.get("amount")
    try:
        amount = Decimal(amount)
    except (InvalidOperation, TypeError):
        messages.error(request, "You entered invalid amount.")
        return redirect("listing_detail", listing_id=listing_id)

    if amount < 0:
        messages.error(request, "Amount should not be a negative number.")

    current_bid = highest_bid(listing)
    if current_bid is None:
        if amount < listing.starting_bid:
            messages.error(request, "Invalid bid.")
            return redirect("listing_detail", listing_id=listing_id)
    else:
        if amount <= current_bid.amount:
            messages.error(request, "You cannot bid at an amount lower than the previous bid.")
            return redirect("listing_detail", listing_id=listing_id)

    Bid.objects.create(bidder=request.user, listing=listing, amount=amount)

    return redirect("listing_detail", listing_id=listing_id)


# Create a comment
@login_required
def add_comment(request, listing_id):
    if request.method != "POST":
        return redirect("listing_detail", listing_id=listing_id)
    
    listing = get_object_or_404(Listing, id=listing_id)

    if not listing.is_active:
        messages.error(request, "This listing is closed. No further comment allowed.")
        return redirect("listing_detail", listing_id=listing_id)

    content = request.POST.get("content")
    if not content or not content.strip():
        messages.error(request, "Invalid submission. The content cannot be blank.")
        return redirect("listing_detail", listing_id=listing_id)

    Comment.objects.create(
        author=request.user,
        listing=listing,
        content=content.strip()
    )

    return redirect("listing_detail", listing_id=listing_id)


# Create categories for listings
def categories(request):
    categories = Category.objects.all()

    return render(request, "auctions/categories.html", {
        "categories": categories
    })


# Create a category_detail and put all the active listings belonging to a category inside this category_detail
def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    listings = category.listings.filter(is_active=True)
    for listing in listings:
        bid = highest_bid(listing)
        if bid is not None:
            listing.current_bid = bid.amount
        else:
            listing.current_bid = listing.starting_bid

    return render(request, "auctions/category_detail.html", {
        "category": category,
        "listings": listings
    })
