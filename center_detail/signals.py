# In your_app/signals.py

from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Subscription # Import your Subscription model

@receiver(post_save, sender=Subscription)
def delete_subscription_cache(sender, instance, **kwargs):
    """
    Deletes the subscription status cache when a Subscription instance is saved.
    """
    # The 'instance' is the Subscription object that was just saved.
    # We need to get the user associated with this subscription.
    # Based on your API response, the user is linked via center_detail.
    try:
        user = instance.center.user_set.first() # Adjust this query based on your actual model relationships
        if user:
            cache_key = f'subscription_status_{user.id}'
            print(f"Deleting cache for key: {cache_key}") # For debugging
            cache.delete(cache_key)
    except AttributeError:
        # Handle cases where the relationship might not be straightforward
        # or if the objects are not linked as expected.
        pass