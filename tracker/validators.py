from django.core.exceptions import ValidationError

# Custom validators for the tracker app

# This validator ensures that the amount entered for a spending is a positive number.
def validate_positive_amount(amount):
    if amount <= 0:
        raise ValidationError(
            "The amount must be a positive number.",
            params={'amount': amount},
        )

# This validator ensures that the user does not exceed the maximum number of categories.
def validate_maximum_categories(owner):
    from .models import Category
    count = Category.objects.filter(owner=owner).count()
    if count >= 20:
        raise ValidationError("Maximum category limit reached.")