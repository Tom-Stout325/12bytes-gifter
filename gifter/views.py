from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
import calendar
from accounts.utils import ensure_profile
from django.urls import reverse_lazy, reverse


from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from .forms import WishlistItemForm, BoardPostForm, BoardCommentForm
from .models import WishlistItem, BoardPost, BoardComment
from accounts.models import Family, Profile







# ---------------------------
# Helpers
# ---------------------------

def _today():
    # Use timezone-aware “today” for consistency across pages
    return timezone.localdate()

def _next_occurrence(d: date) -> date:
    """
    Return the next occurrence (this year or next) for a given month/day date.
    """
    if not d:
        return None
    today = _today()
    this_year = date(today.year, d.month, d.day)
    return this_year if this_year >= today else date(today.year + 1, d.month, d.day)


# ---------------------------
# Wishlist CRUD + actions
# ---------------------------

@login_required
def add_wishlist_item(request, username):
    """
    Create a new wishlist item for the target user's profile.
    Rules:
    - You can add items to your own wishlist.
    - A Parent can add items for a Child in their same Family (or by whatever
      your Profile.can_edit_profile() rule allows).
    """
    viewer_profile = request.user.profile
    if not viewer_profile.is_approved:
        return redirect("accounts:pending_approval")

    target_user = get_object_or_404(User, username=username)
    target_profile = get_object_or_404(Profile, user=target_user)



    # if not target_profile.is_approved:
    #     messages.error(request, "Test")
    #     if target_user == request.user:
    #         return redirect("accounts:profile_edit")
    #     return redirect("gifter:all_families")




    if not viewer_profile.can_edit_profile(target_profile):
        messages.error(request, "You do not have permission to add items to this wishlist.")
        return redirect("accounts:profile_detail", username=target_user.username)

    if request.method == "POST":
        form = WishlistItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.profile = target_profile
            item.save()
            messages.success(request, "Item added to wishlist.")
            return redirect("accounts:profile_detail", username=target_user.username)
    else:
        form = WishlistItemForm()

    return render(request, "gifter/wishlist_item_form.html", {"form": form, "target_profile": target_profile})


@login_required
def edit_wishlist_item(request, pk):
    """
    Edit an existing wishlist item.
    Only allowed if the viewer can edit the wishlist owner's profile.
    """
    viewer_profile = request.user.profile
    if not viewer_profile.is_approved:
        return redirect("accounts:pending_approval")

    item = get_object_or_404(WishlistItem, pk=pk)
    target_profile = item.profile
    target_user = target_profile.user



    # if not target_profile.is_approved:
    #     messages.error(request, "Ttest")
    #     if target_user == request.user:
    #         return redirect("accounts:profile_edit")
    #     return redirect("gifter:all_families")



    if not viewer_profile.can_edit_profile(target_profile):
        messages.error(request, "You do not have permission to edit this wishlist.")
        return redirect("accounts:profile_detail", username=target_user.username)

    if request.method == "POST":
        form = WishlistItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Wishlist item updated.")
            return redirect("accounts:profile_detail", username=target_user.username)
    else:
        form = WishlistItemForm(instance=item)

    return render(request, "gifter/wishlist_item_form.html", {"form": form, "target_profile": target_profile, "item": item})


@login_required
def delete_wishlist_item(request, pk):
    """
    Delete an existing wishlist item (POST only).
    Only allowed if the viewer can edit the wishlist owner's profile.
    """
    viewer_profile = request.user.profile
    if not viewer_profile.is_approved:
        return redirect("accounts:pending_approval")

    item = get_object_or_404(WishlistItem, pk=pk)
    target_profile = item.profile
    target_user = target_profile.user

    if request.method != "POST":
        return HttpResponseForbidden("POST required.")

    if not viewer_profile.can_edit_profile(target_profile):
        messages.error(request, "You do not have permission to delete this wishlist item.")
        return redirect("accounts:profile_detail", username=target_user.username)

    item.delete()
    messages.success(request, "Wishlist item deleted.")
    return redirect("accounts:profile_detail", username=target_user.username)


@login_required
def claim_wishlist_item(request, pk):
    """
    Claim an item (POST only).
    Parents can claim on others; children can claim for others, but templates
    should hide purchase/claim details according to your rule.
    """
    viewer_profile = request.user.profile
    if not viewer_profile.is_approved:
        return redirect("accounts:pending_approval")

    item = get_object_or_404(WishlistItem, pk=pk)

    if request.method != "POST":
        return HttpResponseForbidden("POST required.")

    try:
        item.claim(viewer_profile)
        item.save()
        messages.success(request, "You claimed this item.")
    except PermissionError as e:
        messages.error(request, str(e))

    return redirect("accounts:profile_detail", username=item.profile.user.username)


@login_required
def unclaim_wishlist_item(request, pk):
    """
    Unclaim an item you previously claimed (POST only).
    """
    viewer_profile = request.user.profile
    if not viewer_profile.is_approved:
        return redirect("accounts:pending_approval")

    item = get_object_or_404(WishlistItem, pk=pk)

    if request.method != "POST":
        return HttpResponseForbidden("POST required.")

    try:
        item.unclaim(viewer_profile)
        item.save()
        messages.success(request, "You unclaimed this item.")
    except PermissionError as e:
        messages.error(request, str(e))

    return redirect("accounts:profile_detail", username=item.profile.user.username)


@login_required
def mark_purchased_wishlist_item(request, pk):
    """
    Mark an item as purchased (POST only).
    Permission check happens in model helper or here as needed.
    """
    viewer_profile = request.user.profile
    if not viewer_profile.is_approved:
        return redirect("accounts:pending_approval")

    item = get_object_or_404(WishlistItem, pk=pk)

    if request.method != "POST":
        return HttpResponseForbidden("POST required.")

    try:
        item.mark_purchased(viewer_profile)
        item.save()
        messages.success(request, "Marked purchased.")
    except PermissionError as e:
        messages.error(request, str(e))

    return redirect("accounts:profile_detail", username=item.profile.user.username)


@login_required
def clear_purchased_wishlist_item(request, pk):
    """
    Clear purchased state (POST only).
    """
    viewer_profile = request.user.profile
    if not viewer_profile.is_approved:
        return redirect("accounts:pending_approval")

    item = get_object_or_404(WishlistItem, pk=pk)

    if request.method != "POST":
        return HttpResponseForbidden("POST required.")

    try:
        item.clear_purchased(viewer_profile)
        item.save()
        messages.success(request, "Purchase cleared.")
    except PermissionError as e:
        messages.error(request, str(e))

    return redirect("accounts:profile_detail", username=item.profile.user.username)


# ---------------------------
# Views of lists
# ---------------------------

@login_required
def view_wishlist(request, username):
    """
    Direct view of a single user's wishlist (if you still link to it).
    """
    viewer_profile = request.user.profile
    if not viewer_profile.is_approved:
        return redirect("accounts:pending_approval")

    target_user = get_object_or_404(User, username=username)
    target_profile = get_object_or_404(Profile, user=target_user)

    return redirect("accounts:profile_detail", username=username)


@login_required
def unclaimed_wishlist(request):
    """
    Optional helper: list of currently unclaimed items across your family (or globally).
    Adjust as needed to match your policy.
    """
    viewer = request.user.profile
    if not viewer.is_approved:
        return redirect("accounts:pending_approval")

    # Example: parents see all families; children see all as well (per your rule).
    items = (
        WishlistItem.objects.filter(is_claimed=False)
        .select_related("profile", "profile__user")
        .order_by("profile__user__first_name", "title")
    )[:50]

    return render(request, "gifter/unclaimed_wishlist.html", {"items": items})


# ---------------------------
# Family pages
# ---------------------------

def _today():
    return timezone.localdate()

def _next_occurrence(d: date) -> date | None:
    if not d:
        return None
    today = _today()
    this_year = date(today.year, d.month, d.day)
    return this_year if this_year >= today else date(today.year + 1, d.month, d.day)





@login_required
def family_detail(request, slug):
    """
    NEW RULE: Parents and Children can view ANY family.
    (Privacy for purchase/claimed/notes is enforced at the profile/wishlist template level.)
    """
    viewer = request.user.profile
    fam = get_object_or_404(Family, slug=slug)

    # No visibility restriction now; only require approval to reach here
    if not viewer.is_approved:
        return redirect("accounts:pending_approval")

    qs = (
        Profile.objects.filter(family=fam, is_approved=True)
        .select_related("user")
        .order_by("role", "user__first_name", "user__last_name")
    )
    parents = [p for p in qs if p.role == Profile.ROLE_PARENT]
    kids = [p for p in qs if p.role == Profile.ROLE_CHILD]

    # Build next 60-day upcoming events (to match All Families)
    today = timezone.localdate()
    lookahead = today + timedelta(days=60)
    upcoming_events = []
    for person in qs:
        if person.birthday:
            bd = _next_occurrence(person.birthday)
            if bd and today <= bd <= lookahead:
                upcoming_events.append({
                    "type": "birthday",
                    "date": bd,
                    "label": f"{person.user.first_name}'s Birthday",
                    "person": person,
                })
        if person.anniversary and person.role == Profile.ROLE_PARENT:
            ad = _next_occurrence(person.anniversary)
            if ad and today <= ad <= lookahead:
                label = f"{fam.display_name} Anniversary" if fam.display_name else "Anniversary"
                upcoming_events.append({
                    "type": "anniversary",
                    "date": ad,
                    "label": label,
                    "person": person,
                })
    upcoming_events.sort(key=lambda e: e["date"])

    recent_items = (
        WishlistItem.objects.filter(profile__family=fam)
        .select_related("profile", "profile__user")
        .order_by("-created_at")[:12]
    )

    return render(
        request,
        "gifter/family_detail.html",
        {
            "family": fam,
            "parents": parents,
            "kids": kids,
            "upcoming_events": upcoming_events,
            "recent_items": recent_items,
            "viewer": viewer,
        },
    )



@login_required
@ensure_profile(required_family=True)
def family_home(request):
    viewer = request.user.profile
    if not viewer.family:
        messages.info(request, "Please join or be assigned to a family.")
        return redirect("gifter:all_families")

    return redirect("gifter:family_detail", slug=viewer.family.slug)


@login_required
@ensure_profile(required_family=True)
def family_management(request):
    viewer = request.user.profile
    if not (viewer.user.is_superuser or viewer.user.is_staff):
        return redirect("gifter:all_families")

    families = Family.objects.select_related("parent1", "parent2").order_by("display_name")
    return render(request, "gifter/family_management.html", {"families": families})


@login_required
def family_upcoming(request, months=2):
    """
    Show upcoming birthdays and anniversaries for the next `months` months (default 2).
    Intended for a top-card in the all_families view or as a partial.
    """
    viewer = request.user.profile
    if not viewer.is_approved:
        return redirect("accounts:pending_approval")

    today = _today()
    lookahead = today + timedelta(days=30 * int(months))

    # Build a simple list of events with labels and a single 'avatar_profile' to render.
    events = []
    for prof in (
        Profile.objects.filter(is_approved=True)
        .select_related("user", "family")
        .order_by("family__display_name", "user__first_name")
    ):
        # Birthdays
        if prof.birthday:
            d = _next_occurrence(prof.birthday)
            if d and today <= d <= lookahead:
                events.append({
                    "type": "birthday",
                    "date": d,
                    "label": f"{prof.user.first_name}'s Birthday",
                    "avatar_profile": prof,
                    "profile": prof,
                })

        # Anniversaries (shown once per family per date; basic dedupe)
        if prof.anniversary and prof.family_id:
            d = _next_occurrence(prof.anniversary)
            if d and today <= d <= lookahead:
                events.append({
                    "type": "anniversary",
                    "date": d,
                    "label": f"{prof.family.display_name} Anniversary" if prof.family and prof.family.display_name else "Anniversary",
                    "avatar_profile": prof,
                    "profile": prof,
                })

    events.sort(key=lambda e: e["date"])
    return render(request, "gifter/family_upcoming.html", {"events": events})




def _today():
    return timezone.localdate()

def _next_occurrence(d):
    if not d:
        return None
    today = _today()
    try:
        this_year = d.replace(year=today.year)
    except ValueError:
        this_year = d.replace(year=today.year, day=28)  # Feb 29 safety
    return this_year if this_year >= today else this_year.replace(year=today.year + 1)

@login_required
def all_families(request):
    """
    NEW RULE: Parents and Children can view ALL families.
    Privacy for claimed/purchased/notes is enforced elsewhere via flags.
    """
    viewer = request.user.profile
    if not viewer.is_approved:
        return redirect("accounts:pending_approval")

    today = _today()
    lookahead = today + timedelta(days=60)

    # Everyone sees all families
    families_qs = Family.objects.select_related("parent1", "parent2").order_by("display_name")

    global_events = []
    families_enriched = []

    for fam in families_qs:
        members_qs = (
            Profile.objects.filter(family=fam, is_approved=True)
            .select_related("user")
            .order_by("role", "user__first_name", "user__last_name")
        )
        members = list(members_qs)
        parents = [p for p in members if p.role == Profile.ROLE_PARENT]
        kids = [p for p in members if p.role == Profile.ROLE_CHILD]

        # Representative avatar for family tile
        card_avatar = parents[0] if parents else (members[0] if members else None)

        # Per-family next event + aggregate global list (next 60 days)
        next_event = None
        for person in members:
            if person.birthday:
                bd = _next_occurrence(person.birthday)
                if bd and today <= bd <= lookahead:
                    cand = {"type": "birthday", "date": bd, "label": f"{person.user.first_name}'s Birthday", "person": person}
                    if next_event is None or bd < next_event["date"]:
                        next_event = cand
                    global_events.append(cand)
            if person.anniversary and person.role == Profile.ROLE_PARENT:
                ad = _next_occurrence(person.anniversary)
                if ad and today <= ad <= lookahead:
                    label = f"{fam.display_name} Anniversary" if fam.display_name else "Anniversary"
                    cand = {"type": "anniversary", "date": ad, "label": label, "person": person}
                    if next_event is None or ad < next_event["date"]:
                        next_event = cand
                    global_events.append(cand)

        families_enriched.append({
            "family": fam,
            "card_avatar": card_avatar,
            "next_event": next_event,
            "parents": parents,
            "kids": kids,
        })

    global_events.sort(key=lambda e: e["date"])
    global_next5 = global_events[:5]

    return render(
        request,
        "gifter/all_families.html",
        {
            "families_enriched": families_enriched,
            "global_next5": global_next5,
            "viewer": viewer,
        },
    )
    
    

@login_required
def wishlist_item_detail(request, pk):
    """
    Show a detailed view of a single wishlist item.

    Anyone who can view the profile can view this page.
    Claim/purchase visibility still respects can_view_purchase_info.
    """
    viewer_profile = request.user.profile
    if not viewer_profile.is_approved:
        return redirect("accounts:pending_approval")

    item = (
        WishlistItem.objects
        .select_related("profile__user", "claimed_by__user", "purchased_by__user")
        .get(pk=pk)
    )

    target_profile = item.profile
    target_user = target_profile.user

    context = {
        "item": item,
        "target_profile": target_profile,
        "target_user": target_user,
        "viewer_profile": viewer_profile,
        "can_view_purchase_info": viewer_profile.can_view_purchase_info_for(target_profile),
        "can_view_private_notes": viewer_profile.can_view_private_notes_for(target_profile),
        "can_edit_wishlist": viewer_profile.can_edit_profile(target_profile),
    }
    return render(request, "gifter/wishlist_item_detail.html", context)





# ---------------------------------------------------------------------
# Board permissions helpers
# ---------------------------------------------------------------------
def user_can_edit_post(user, post: BoardPost) -> bool:
    return user.is_authenticated and (user == post.author or user.is_staff)


def user_can_edit_comment(user, comment: BoardComment) -> bool:
    return user.is_authenticated and (user == comment.author or user.is_staff)


# ---------------------------------------------------------------------
# Board post views
# ---------------------------------------------------------------------
class BoardPostListView(LoginRequiredMixin, ListView):
    """
    Global board: show posts from the last 30 days, newest first.
    """
    model = BoardPost
    template_name = "gifter/board_list.html"
    context_object_name = "posts"
    paginate_by = 10

    def get_queryset(self):
        cutoff = timezone.now() - timedelta(days=30)
        return BoardPost.objects.filter(created_at__gte=cutoff).select_related("author")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["archive_mode"] = False
        return ctx


class BoardPostArchiveView(LoginRequiredMixin, ListView):
    """
    Archive view: posts older than 30 days.
    """
    model = BoardPost
    template_name = "gifter/board_list.html"
    context_object_name = "posts"
    paginate_by = 10

    def get_queryset(self):
        cutoff = timezone.now() - timedelta(days=30)
        return BoardPost.objects.filter(created_at__lt=cutoff).select_related("author")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["archive_mode"] = True
        return ctx


class BoardPostDetailView(LoginRequiredMixin, DetailView):
    model = BoardPost
    template_name = "gifter/board_detail.html"
    context_object_name = "post"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        post = self.object
        ctx["comments"] = post.comments.select_related("author")
        ctx["comment_form"] = BoardCommentForm()
        ctx["can_edit_post"] = user_can_edit_post(self.request.user, post)
        return ctx


class BoardPostCreateView(LoginRequiredMixin, CreateView):
    model = BoardPost
    form_class = BoardPostForm
    template_name = "gifter/board_form.html"

    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, "Announcement posted.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("gifter:board_detail", args=[self.object.pk])


class BoardPostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = BoardPost
    form_class = BoardPostForm
    template_name = "gifter/board_form.html"

    def test_func(self):
        post = self.get_object()
        return user_can_edit_post(self.request.user, post)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to edit this post.")
        return redirect("gifter:board_detail", pk=self.get_object().pk)

    def form_valid(self, form):
        messages.success(self.request, "Announcement updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("gifter:board_detail", args=[self.object.pk])


class BoardPostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = BoardPost
    template_name = "gifter/board_confirm_delete.html"
    success_url = reverse_lazy("gifter:board_list")

    def test_func(self):
        post = self.get_object()
        return user_can_edit_post(self.request.user, post)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to delete this post.")
        return redirect("gifter:board_detail", pk=self.get_object().pk)

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Announcement deleted.")
        return super().delete(request, *args, **kwargs)


# ---------------------------------------------------------------------
# Comment views (function-based for simplicity)
# ---------------------------------------------------------------------
@login_required
def board_comment_create(request, post_id):
    post = get_object_or_404(BoardPost, pk=post_id)

    if request.method == "POST":
        form = BoardCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            messages.success(request, "Comment added.")
    return redirect("gifter:board_detail", pk=post.pk)


@login_required
def board_comment_update(request, pk):
    comment = get_object_or_404(BoardComment, pk=pk)

    if not user_can_edit_comment(request.user, comment):
        messages.error(request, "You do not have permission to edit this comment.")
        return redirect("gifter:board_detail", pk=comment.post.pk)

    if request.method == "POST":
        form = BoardCommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, "Comment updated.")
            return redirect("gifter:board_detail", pk=comment.post.pk)
    else:
        form = BoardCommentForm(instance=comment)

    return render(
        request,
        "gifter/board_comment_form.html",
        {"form": form, "comment": comment},
    )


@login_required
def board_comment_delete(request, pk):
    comment = get_object_or_404(BoardComment, pk=pk)

    if not user_can_edit_comment(request.user, comment):
        messages.error(request, "You do not have permission to delete this comment.")
        return redirect("gifter:board_detail", pk=comment.post.pk)

    post_pk = comment.post.pk
    if request.method == "POST":
        comment.delete()
        messages.success(request, "Comment deleted.")
    return redirect("gifter:board_detail", pk=post_pk)




@login_required
def calendar_view(request, year=None, month=None):
    """
    Family calendar:
    - Birthdays: 🎂 First name only
    - Anniversaries:
        * Parents with a Family: 💍 Family.display_name (e.g. "Tom & Leslie"), once per couple
        * Others: 💍 First name
    - Announcements: 📢 BoardPost title (current month only)
    """
    today = timezone.localdate()

    # Pick year / month
    if year is None or month is None:
        year = today.year
        month = today.month
    else:
        year = int(year)
        month = int(month)

    # Basic month navigation
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    month_label = date(year, month, 1).strftime("%B %Y")

    # ---- Collect events into a {date: [events]} dict ----
    events_by_date: dict[date, list[dict]] = {}

    def add_event(dt: date, ev_type: str, label: str, **extra):
        events_by_date.setdefault(dt, []).append(
            {
                "type": ev_type,
                "label": label,
                **extra,
            }
        )

    # Helper for short names
    def short_name(profile: Profile) -> str:
        u = profile.user
        if u.first_name:
            return u.first_name
        full = u.get_full_name() or u.username
        return (full.split()[0] if full else "") or "User"

    # Profiles with birthdays/anniversaries
    profiles_with_bday = Profile.objects.exclude(birthday__isnull=True)
    profiles_with_ann = Profile.objects.exclude(anniversary__isnull=True)

    # Birthdays (recurring yearly, first name only)
    for p in profiles_with_bday:
        if p.birthday.month != month:
            continue
        dt = date(year, month, p.birthday.day)
        add_event(dt, "birthday", short_name(p), profile=p)

    # Anniversaries (recurring yearly, deduped per couple/family)
    seen_anniversaries = set()

    for p in profiles_with_ann:
        if p.anniversary.month != month:
            continue

        day = p.anniversary.day

        if p.family and p.role == Profile.ROLE_PARENT:
            # one entry per family + day
            key = ("family", p.family_id, day)
            label = p.family.display_name or short_name(p) or "Anniversary"
        else:
            key = ("profile", p.id, day)
            label = short_name(p) or "Anniversary"

        if key in seen_anniversaries:
            continue
        seen_anniversaries.add(key)

        dt = date(year, month, day)
        add_event(dt, "anniversary", label, profile=p)

    # Announcements (BoardPost created in this month)
    posts = BoardPost.objects.filter(
        created_at__year=year,
        created_at__month=month,
    ).select_related("author")

    for post in posts:
        dt = post.created_at.date()
        label = post.title or "Announcement"
        add_event(dt, "announcement", label, post=post)

    # ---- Build calendar weeks with attached events ----
    cal = calendar.Calendar(firstweekday=0)  # Monday=0 if you want
    weeks = []
    for week in cal.monthdatescalendar(year, month):
        row = []
        for day in week:
            row.append(
                {
                    "date": day,
                    "events": events_by_date.get(day, []),
                    "in_current_month": (day.month == month),
                }
            )
        weeks.append(row)
    
        has_events = any(
            cell["events"]
            for week in weeks
            for cell in week
            if cell["in_current_month"]
        )

    context = {
        "today": today,
        "year": year,
        "month": month,
        "month_label": month_label,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
        "weeks": weeks,
        "has_events": has_events,
    }

    return render(request, "gifter/calendar.html", context)