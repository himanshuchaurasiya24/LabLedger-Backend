from django.core.cache import cache

# Let's say you need to clear the cache for the user with ID 1
user_id = 1
key_to_delete = f'subscription_status_{user_id}'

# Check if the key exists (optional)
if cache.get(key_to_delete):
  print(f"Found key: {key_to_delete}. Deleting now.")
  cache.delete(key_to_delete)
  print("Key deleted.")
else:
  print(f"Key {key_to_delete} not found in cache.")