from django.db import models
from django.contrib.auth.models import User

class Spending(models.Model):
    class SpentForChoices(models.TextChoices):
        SELF = 'SELF', 'For Self'
        HOME = 'HOME', 'For Home'
        WORK = 'WORK', 'For Work'
        OTHER = 'OTHER', 'For Other'

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='spendings')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    category = models.CharField(max_length=255)
    spent_for = models.CharField(
        max_length=10,
        choices=SpentForChoices.choices,
        default=SpentForChoices.SELF
    )

    def __str__(self):
        return f"{self.owner.username}: {self.category}, {self.amount} for {self.spent_for}"
    
class ToBuyItem(models.Model):
    class ToBuyForChoices(models.TextChoices):
        SELF = 'SELF', 'For Self'
        HOME = 'HOME', 'For Home'
        WORK = 'WORK', 'For Work'
        OTHER = 'OTHER', 'For Other'

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tobuyitems')
    category = models.CharField(max_length=255)
    tobuy_for = models.CharField(
        max_length=10,
        choices=ToBuyForChoices.choices,
        default=ToBuyForChoices.SELF
    )

    def __str__(self):
        return f"{self.owner.username}: {self.category} for {self.tobuy_for}"