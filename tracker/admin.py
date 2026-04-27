from django.contrib import admin
from .models import Budget, Category, Spending, ToBuyItem

admin.site.register(Category)
admin.site.register(Spending)
admin.site.register(ToBuyItem)
admin.site.register(Budget)
