from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.db.models import DecimalField, Sum, OuterRef, Subquery
from django.db.models.functions import Coalesce

from tracker.validators import validate_positive_amount

# Models for the tracker app

# The Category model represents a spending category that belongs to a user.
class Category(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=255)

    created = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('owner', 'name')  # Ensure each user can't have duplicate category names

    def __str__(self):
        return f"{self.owner.username}: {self.name}"

# The Spending model represents a spending entry made by a user, including details such as amount, date, category, and () the spending was for.
class Spending(models.Model):
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='spendings')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[validate_positive_amount])
    date = models.DateField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='spendings')
    title = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return f"{self.owner.username}: {self.title} ({self.category}), {self.amount} on {self.date}"
    
# The ToBuyItem model represents an item that a user intends to buy in the future, including details such as category and () the item is for.
class ToBuyItem(models.Model):
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tobuyitems')
    title = models.CharField(max_length=255, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='tobuyitems')

    def __str__(self):
        return f"{self.owner.username}: {self.title} ({self.category}) - To Buy Item."
    

class Budget(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='budgets', null=True, blank=True)
    
    budget_amount = models.DecimalField(max_digits=12, decimal_places=2)
    actual_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    month = models.IntegerField(default=1)
    year = models.IntegerField(default=2026)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'category', 'month', 'year'],
                name='unique_budget_per_category_month_year'
            ),
            models.UniqueConstraint(
                fields=['owner', 'month', 'year'],
                condition=models.Q(category__isnull=True),
                name='unique_budget_per_month_year_no_category'
            ),
        ]
    def __str__(self):
        category_name = self.category.name if self.category else "No Category"
        return f"{self.owner.username}: {category_name} - {self.budget_amount} in {self.month}/{self.year}"
