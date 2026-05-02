from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.db.models import F, Sum
from django.contrib.auth.models import User

from .models import Budget, Category, Spending

@receiver(post_save, sender=User)
def initialize_budget_for_new_user(sender, instance, created, **kwargs):
    if created:
        Budget.objects.get_or_create(
            owner=instance,
            category=None,
            month=instance.date_joined.month,
            year=instance.date_joined.year,
            defaults={'budget_amount': 0.00}
        )


@receiver(post_save, sender=Category)
def initialize_budget_for_new_category(sender, instance, created, **kwargs):
    if created:
        Budget.objects.get_or_create(
            owner=instance.owner,
            category=instance,
            month=instance.created.month,
            year=instance.created.year,
            defaults={'budget_amount': 0.00}
        )
        
def update_actual_spent_for_budget(owner, category, month, year, delta):
    if delta == 0:
        return
    
    if category:
        Budget.objects.filter(
            owner=owner,
            category=category,
            month=month,
            year=year
        ).update(actual_spent=F('actual_spent') + delta)

    Budget.objects.filter(
        owner=owner,
        category=None,
        month=month,
        year=year
    ).update(actual_spent=F('actual_spent') + delta)

@receiver(pre_save, sender=Spending)
def cal_delta_on_spending_update(sender, instance, **kwargs):
    if instance.pk:
        old_obj = Spending.objects.get(pk=instance.pk)
        instance._old_data = {
            'amount': old_obj.amount,
            'category': old_obj.category,
            'month': old_obj.date.month,
            'year': old_obj.date.year,
        }
    else:
        instance._old_data = None

@receiver(post_save, sender=Spending)
def apply_delta_on_spending_save(sender, instance, created, **kwargs):
    if created:
        delta = instance.amount
    else:
        old_data = instance._old_data
        if old_data:
            if (old_data['category'] != instance.category or
                old_data['month'] != instance.date.month or
                old_data['year'] != instance.date.year):
                # If category, month, or year has changed, we need to reverse the old amount from the old budget and add the new amount to the new budget.
                update_actual_spent_for_budget(
                    owner=instance.owner,
                    category=old_data['category'],
                    month=old_data['month'],
                    year=old_data['year'],
                    delta=-old_data['amount']
                )
                delta = instance.amount
            else:
                delta = instance.amount - old_data['amount']
        else:
            delta = instance.amount
    
    update_actual_spent_for_budget(
        owner=instance.owner,
        category=instance.category,
        month=instance.date.month,
        year=instance.date.year,
        delta=delta
    )
    

@receiver(post_delete, sender=Spending)
def apply_delta_on_spending_delete(sender, instance, **kwargs):
    delta = -instance.amount
    update_actual_spent_for_budget(
        owner=instance.owner,
        category=instance.category,
        month=instance.date.month,
        year=instance.date.year,
        delta=delta
    )


