import django_filters
from .models import Spending, ToBuyItem

# Filters for Spendings and ToBuyItems

# The SpendingFilter allows users to filter their spendings based on { amount, date, category, and () the spending was for }.
class SpendingFilter(django_filters.FilterSet):
    min_amount = django_filters.NumberFilter(field_name="amount", lookup_expr='gte')
    max_amount = django_filters.NumberFilter(field_name="amount", lookup_expr='lte')
    
    min_date = django_filters.DateFilter(field_name="date", lookup_expr='gte')
    max_date = django_filters.DateFilter(field_name="date", lookup_expr='lte')

    month = django_filters.NumberFilter(field_name="date", lookup_expr='month')
    year = django_filters.NumberFilter(field_name="date", lookup_expr='year')
    
    spent_for = django_filters.CharFilter(field_name='spent_for', lookup_expr='icontains')
    category = django_filters.CharFilter(field_name='category__name', lookup_expr='icontains')

    class Meta:
        model = Spending
        fields = ['category', 'date', 'spent_for']

# The ToBuyItemFilter allows users to filter their to-buy items based on { category & () the item is for }.
class ToBuyItemFilter(django_filters.FilterSet):
    tobuy_for = django_filters.CharFilter(field_name='tobuy_for', lookup_expr='icontains')
    category = django_filters.CharFilter(field_name='category__name', lookup_expr='icontains')
    class Meta:
        model = ToBuyItem
        fields = ['category', 'tobuy_for']
        