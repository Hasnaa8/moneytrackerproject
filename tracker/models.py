from django.db import models
from django.contrib.auth.models import User

from tracker.validators import validate_positive_amount

# Models for the tracker app

# The Category model represents a spending category that belongs to a user.
class Category(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = ('owner', 'name')  # Ensure each user can't have duplicate category names

    def __str__(self):
        return f"{self.owner.username}: {self.name}"

# The Spending model represents a spending entry made by a user, including details such as amount, date, category, and () the spending was for.
class Spending(models.Model):
    class SpentForChoices(models.TextChoices):
        SELF = 'SELF', 'For Self'
        HOME = 'HOME', 'For Home'
        WORK = 'WORK', 'For Work'
        OTHER = 'OTHER', 'For Other'

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='spendings')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[validate_positive_amount])
    date = models.DateField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='spendings')
    title = models.CharField(max_length=255, blank=True)
    spent_for = models.CharField(
        max_length=10,
        choices=SpentForChoices.choices,
        default=SpentForChoices.SELF
    )

    def __str__(self):
        return f"{self.owner.username}: {self.title} ({self.category}), {self.amount} for {self.spent_for}"
    
# The ToBuyItem model represents an item that a user intends to buy in the future, including details such as category and () the item is for.
class ToBuyItem(models.Model):
    class ToBuyForChoices(models.TextChoices):
        SELF = 'SELF', 'For Self'
        HOME = 'HOME', 'For Home'
        WORK = 'WORK', 'For Work'
        OTHER = 'OTHER', 'For Other'

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tobuyitems')
    title = models.CharField(max_length=255, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='tobuyitems')
    tobuy_for = models.CharField(
        max_length=10,
        choices=ToBuyForChoices.choices,
        default=ToBuyForChoices.SELF
    )

    def __str__(self):
        return f"{self.owner.username}: {self.title} ({self.category}) for {self.tobuy_for}"