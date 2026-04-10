"""Signals for center_detail app."""

from datetime import date, timedelta

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from .models import ActiveSubscription, CenterDetail, SubscriptionPlan, get_free_plan


@receiver(post_save, sender=CenterDetail)
def ensure_default_active_subscription(sender, instance, created, **kwargs):
	"""Every center must always have exactly one active subscription."""
	if created:
		free_plan = get_free_plan()
		ActiveSubscription.objects.get_or_create(
			center_detail=instance,
			defaults={
				"subscription_plan": free_plan,
				"plan_activated_on": date.today(),
			},
		)


@receiver(post_delete, sender=ActiveSubscription)
def recreate_default_subscription_on_delete(sender, instance, **kwargs):
	"""
	If an active subscription is deleted directly, recreate a FREE fallback
	for the same center (unless center itself is gone).
	"""
	center_id = instance.center_detail_id

	def _recreate_if_center_still_exists():
		center = CenterDetail.objects.filter(pk=center_id).first()
		if not center:
			return

		free_plan = get_free_plan()
		ActiveSubscription.objects.get_or_create(
			center_detail=center,
			defaults={
				"subscription_plan": free_plan,
				"plan_activated_on": date.today(),
			},
		)

	transaction.on_commit(_recreate_if_center_still_exists)


@receiver(pre_delete, sender=SubscriptionPlan)
def fallback_active_subscriptions_before_plan_delete(sender, instance, **kwargs):
	"""
	Before deleting any plan, move all active subscriptions to FREE.
	If FREE itself is deleted, rotate FREE first, then remap.
	"""
	if instance.name == "FREE":
		# Temporarily rename the plan being deleted so a replacement FREE can be created.
		temp_name = f"FREE__DELETING__{instance.pk}"
		SubscriptionPlan.objects.filter(pk=instance.pk).update(name=temp_name)

	replacement_free = get_free_plan()
	ActiveSubscription.objects.filter(subscription_plan_id=instance.pk).update(
		subscription_plan=replacement_free,
		plan_activated_on=date.today(),
		plan_expires_on=date.today() + timedelta(days=replacement_free.duration_days),
	)