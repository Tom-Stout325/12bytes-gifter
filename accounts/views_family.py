from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import Family, Profile





from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import Family, Profile


@login_required
def family_detail(request, slug):
    family = get_object_or_404(Family, slug=slug)

    # Profiles for parents (safe getattr in case profile not created yet)
    parent1_profile = getattr(family.parent1, "profile", None)
    parent2_profile = getattr(family.parent2, "profile", None)

    # All members in this family (parents + kids + whoever)
    members_qs = family.members.select_related("user")

    # Children (for the bottom grid)
    kids_qs = members_qs.filter(role="Child")

    # --- Build "Coming Soon" events ---
    today = timezone.localdate()
    lookahead_limit = today + timedelta(days=62)  # ~2 months

    upcoming_events = []

    for member in members_qs:
        # Birthday logic
        if member.birthday:
            # Take this year's birthday
            next_bday = member.birthday.replace(year=today.year)

            # If already happened this year, use next year
            if next_bday < today:
                next_bday = next_bday.replace(year=today.year + 1)

            # If within window, add it
            if today <= next_bday <= lookahead_limit:
                upcoming_events.append({
                    "date": next_bday,
                    "label": "Birthday",
                    "person": member,
                })

        # Anniversary logic (usually only applies to parents)
        if member.anniversary and member.role == "Parent":
            next_anniv = member.anniversary.replace(year=today.year)

            if next_anniv < today:
                next_anniv = next_anniv.replace(year=today.year + 1)

            if today <= next_anniv <= lookahead_limit:
                # We'll word this as "<Parent1> & <Parent2>'s Anniversary",
                # but here we just tag it as "Anniversary" and we'll format the label nicely in template.
                upcoming_events.append({
                    "date": next_anniv,
                    "label": "Anniversary",
                    "person": member,
                })

    # sort by soonest
    upcoming_events.sort(key=lambda e: e["date"])

    # keep only first two
    upcoming_events = upcoming_events[:2]

    context = {
        "family": family,
        "parent1": parent1_profile,
        "parent2": parent2_profile,
        "kids": list(kids_qs),
        "upcoming_events": upcoming_events,
        "today": today,
    }
    return render(request, "gifter/family_detail.html", context)





@login_required
def family_list(request):
    families = Family.objects.all().order_by("display_name")
    context = {
        "families": families,
    }
    return render(request, "gifter/family_list.html", context)
