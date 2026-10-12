from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("listing/<int:listing_id>", views.listing_detail, name="listing_detail"), #Listing
    path("create/", views.create_listing, name="create_listing"), #Listing
    path("watchlist/", views.watchlist, name="watchlist"), #Watchlist
    path("listing/<int:listing_id>/watch/", views.toggle_watchlist, name="toggle_watchlist"), #Watchlist
    path("listing/<int:listing_id>/bid/", views.place_bid, name="place_bid"), #Bidding
    path("listing/<int:listing_id>/close/", views.close_listing, name="close_listing"), #Close Listing
    path("listing/<int:listing_id>/comment/", views.add_comment, name="add_comment"), #Comment
    path("categories/", views.categories, name="categories"), #Categories
    path("category/<int:category_id>/", views.category_detail, name="category_detail") #Category
]

