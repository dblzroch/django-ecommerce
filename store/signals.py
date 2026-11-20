"""Store signals."""

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


@receiver(user_logged_in)
def migrate_anonymous_cart(sender, request, user, **kwargs):
    """Merge anonymous session cart into authenticated user's session."""
    # The session key may change after login (cycle_key), so we need to get
    # the cart from the old session if possible.
    # Django's auth login cycle_key() preserves session data, so cart should be there.
    cart = request.session.get("cart")
    if cart:
        # Cart is already in the session, nothing to migrate
        request.session.modified = True
    # Coupon code also preserved automatically
    # No action needed if session is preserved across login