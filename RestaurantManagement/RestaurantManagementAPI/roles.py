"""Role helpers.

Roles are Django auth groups. Group-name matching is forgiving ("Manager",
"manager", "Delivery crew", "Delivery_Crew" ... all work) so the API behaves
the same on a reviewer's freshly created groups.
"""
from django.contrib.auth.models import Group

MANAGER = 'manager'
DELIVERY_CREW = 'delivery crew'

CANONICAL_NAMES = {MANAGER: 'Manager', DELIVERY_CREW: 'Delivery crew'}


def _norm(name):
    return name.lower().replace('_', ' ').replace('-', ' ').strip()


def user_roles(user):
    if not user or not user.is_authenticated:
        return set()
    return {_norm(n) for n in user.groups.values_list('name', flat=True)}


def is_manager(user):
    """Managers and superusers (admins) can do everything a manager can."""
    return bool(user and user.is_authenticated and
                (user.is_superuser or MANAGER in user_roles(user)))


def is_delivery_crew(user):
    return DELIVERY_CREW in user_roles(user)


def find_group(role):
    for group in Group.objects.all():
        if _norm(group.name) == role:
            return group
    return None


def get_or_create_group(role):
    return find_group(role) or Group.objects.create(name=CANONICAL_NAMES[role])
