from datetime import date

from django.test import TestCase

from .models import ActiveSubscription, CenterDetail, SubscriptionPlan
from .serializers import ActiveSubscriptionSerializer


class ActiveSubscriptionSerializerTests(TestCase):
	def setUp(self):
		self.center = CenterDetail.objects.create(
			center_name="Test Center",
			address="123 Main Street",
			owner_name="Owner",
			owner_phone="9999999999",
		)
		self.plan_one = SubscriptionPlan.objects.create(
			name="Starter",
			plan_index=1,
			duration_days=30,
			price=100,
		)
		self.plan_two = SubscriptionPlan.objects.create(
			name="Growth",
			plan_index=2,
			duration_days=60,
			price=200,
		)

	def test_create_updates_existing_subscription_for_same_center(self):
		first_serializer = ActiveSubscriptionSerializer(
			data={
				"center_detail_id": self.center.pk,
				"subscription_plan_id": self.plan_one.pk,
				"plan_activated_on": date(2026, 5, 1),
			}
		)
		self.assertTrue(first_serializer.is_valid(), first_serializer.errors)
		first_subscription = first_serializer.save()

		second_serializer = ActiveSubscriptionSerializer(
			data={
				"center_detail_id": self.center.pk,
				"subscription_plan_id": self.plan_two.pk,
				"plan_activated_on": date(2026, 5, 10),
			}
		)
		self.assertTrue(second_serializer.is_valid(), second_serializer.errors)
		second_subscription = second_serializer.save()

		self.assertEqual(ActiveSubscription.objects.filter(center_detail=self.center).count(), 1)
		self.assertEqual(first_subscription.pk, second_subscription.pk)
		self.assertEqual(second_subscription.subscription_plan_id, self.plan_two.pk)
