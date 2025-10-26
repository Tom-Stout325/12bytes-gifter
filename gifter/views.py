from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.urls import reverse

from accounts.models import Profile
from django.contrib.auth.models import User
from .forms import WishlistItemForm
from .models import WishlistItem



def home(request):
    return render(request, "home.html")



@login_required
def add_wishlist_item(request, username):
    """
    Create a new wishlist item for the target user's profile.
    Rules:
    - You can add items to your own wishlist.
    - A Parent can add items for a Child in their same Family.
    """

    viewer_profile = get_object_or_404(Profile, user=request.user)
    if not viewer_profile.is_approved:
        return redirect("accounts:pending_approval")

    target_user = get_object_or_404(User, username=username)
    target_profile = get_object_or_404(Profile, user=target_user)

    if not target_profile.is_approved:
        messages.error(request, "This profile is not available yet.")
        return redirect("gifter:home")

    # permission check using your existing business rule
    if not viewer_profile.can_edit_profile(target_profile):
        messages.error(request, "You do not have permission to add items to this wishlist.")
        return redirect("accounts:profile_detail", username=target_user.username)

    if request.method == "POST":
        form = WishlistItemForm(request.POST, request.FILES)
        if form.is_valid():
            wishlist_item = form.save(commit=False)
            wishlist_item.profile = target_profile
            wishlist_item.save()
            messages.success(request, "Wishlist item added.")
            return redirect("accounts:profile_detail", username=target_user.username)
    else:
        form = WishlistItemForm()

    return render(
        request,
        "gifter/wishlist_item_form.html",
        {
            "form": form,
            "target_profile": target_profile,
            "target_user": target_user,
        },
    )


from django.http import HttpResponseForbidden


@login_required
def edit_wishlist_item(request, pk):
    """
    Edit an existing wishlist item.
    Only allowed if the viewer can edit the wishlist owner's profile.
    """
    viewer_profile = get_object_or_404(Profile, user=request.user)
    if not viewer_profile.is_approved:
        return redirect("accounts:pending_approval")

    item = get_object_or_404(WishlistItem, pk=pk)
    target_profile = item.profile  # the profile this item belongs to
    target_user = target_profile.user

    # permission check
    if not viewer_profile.can_edit_profile(target_profile):
        messages.error(request, "You do not have permission to edit this wishlist item.")
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        form = WishlistItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Wishlist item updated.")
            return redirect("accounts:profile_detail", username=target_user.username)
    else:
        form = WishlistItemForm(instance=item)

    return render(
        request,
        "gifter/wishlist_item_form_edit.html",
        {
            "form": form,
            "item": item,
            "target_profile": target_profile,
            "target_user": target_user,
        },
    )


@login_required
def delete_wishlist_item(request, pk):
    """
    Delete an existing wishlist item with a confirmation step.
    Only allowed if the viewer can edit the wishlist owner's profile.
    """
    viewer_profile = get_object_or_404(Profile, user=request.user)
    if not viewer_profile.is_approved:
        return redirect("accounts:pending_approval")

    item = get_object_or_404(WishlistItem, pk=pk)
    target_profile = item.profile
    target_user = target_profile.user

    # permission check
    if not viewer_profile.can_edit_profile(target_profile):
        messages.error(request, "You do not have permission to delete this wishlist item.")
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        # user confirmed delete
        item.delete()
        messages.success(request, "Wishlist item deleted.")
        return redirect("accounts:profile_detail", username=target_user.username)

    # GET -> show confirmation page
    return render(
        request,
        "gifter/wishlist_item_confirm_delete.html",
        {
            "item": item,
            "target_profile": target_profile,
            "target_user": target_user,
        },
    )

@login_required
def claim_wishlist_item(request, pk):
    """
    Parent claims an item: "I'm getting this."
    Rules:
    - Only Parents can claim.
    - Only one claimer at a time.
    - If already claimed by YOU, we’ll allow you to unclaim via a second action (separate view).
    """
    viewer_profile = get_object_or_404(Profile, user=request.user)
    if not viewer_profile.is_approved:
        return redirect("accounts:pending_approval")

    item = get_object_or_404(WishlistItem, pk=pk)
    target_user = item.profile.user

    if request.method != "POST":
        return HttpResponseForbidden("POST required.")

    try:
        item.claim(viewer_profile)
        item.save()
        messages.success(request, "You claimed this item.")
    except PermissionError as e:
        messages.error(request, str(e))

    return redirect("accounts:profile_detail", username=target_user.username)


@login_required
def unclaim_wishlist_item(request, pk):
    """
    Parent unclaims an item.
    - Only Parents can unclaim.
    - Only the claimer OR a Parent who can edit that child's profile can unclaim.
    """
    viewer_profile = get_object_or_404(Profile, user=request.user)
    if not viewer_profile.is_approved:
        return redirect("accounts:pending_approval")

    item = get_object_or_404(WishlistItem, pk=pk)
    target_user = item.profile.user

    if request.method != "POST":
        return HttpResponseForbidden("POST required.")

    try:
        item.unclaim(viewer_profile)
        item.save()
        messages.success(request, "You unclaimed this item.")
    except PermissionError as e:
        messages.error(request, str(e))

    return redirect("accounts:profile_detail", username=target_user.username)


@login_required
def mark_purchased_wishlist_item(request, pk):
    """
    Parent marks an item as purchased.
    - Only Parents can do this.
    """
    viewer_profile = get_object_or_404(Profile, user=request.user)
    if not viewer_profile.is_approved:
        return redirect("accounts:pending_approval")

    item = get_object_or_404(WishlistItem, pk=pk)
    target_user = item.profile.user

    if request.method != "POST":
        return HttpResponseForbidden("POST required.")

    try:
        item.mark_purchased(viewer_profile)
        item.save()
        messages.success(request, "Marked as purchased.")
    except PermissionError as e:
        messages.error(request, str(e))

    return redirect("accounts:profile_detail", username=target_user.username)


@login_required
def clear_purchased_wishlist_item(request, pk):
    """
    Undo purchase.
    - Only Parents can clear purchase state.
    """
    viewer_profile = get_object_or_404(Profile, user=request.user)
    if not viewer_profile.is_approved:
        return redirect("accounts:pending_approval")

    item = get_object_or_404(WishlistItem, pk=pk)
    target_user = item.profile.user

    if request.method != "POST":
        return HttpResponseForbidden("POST required.")

    try:
        item.clear_purchased(viewer_profile)
        item.save()
        messages.success(request, "Purchase cleared.")
    except PermissionError as e:
        messages.error(request, str(e))

    return redirect("accounts:profile_detail", username=target_user.username)
