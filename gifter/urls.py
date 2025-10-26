from django.urls import path
from . import views

app_name = "gifter"

urlpatterns = [
    path("", views.home, name="home"),

    # Wishlist CRUD
    path("wishlist/<str:username>/add/", views.add_wishlist_item, name="add_wishlist_item"),
    path("wishlist/item/<int:pk>/edit/", views.edit_wishlist_item, name="edit_wishlist_item"),
    path("wishlist/item/<int:pk>/delete/", views.delete_wishlist_item, name="delete_wishlist_item"),

    # Claim / purchase actions
    path("wishlist/item/<int:pk>/claim/", views.claim_wishlist_item, name="claim_wishlist_item"),
    path("wishlist/item/<int:pk>/unclaim/", views.unclaim_wishlist_item, name="unclaim_wishlist_item"),
    path("wishlist/item/<int:pk>/purchase/", views.mark_purchased_wishlist_item, name="mark_purchased_wishlist_item"),
    path("wishlist/item/<int:pk>/unpurchase/", views.clear_purchased_wishlist_item, name="clear_purchased_wishlist_item"),
]
