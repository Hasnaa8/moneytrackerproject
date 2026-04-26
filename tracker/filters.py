import django_filters
from .models import Spending

class SpendingFilter(django_filters.FilterSet):
    min_amount = django_filters.NumberFilter(field_name="amount", lookup_expr='gte')
    max_amount = django_filters.NumberFilter(field_name="amount", lookup_expr='lte')
    month = django_filters.NumberFilter(field_name="date", lookup_expr='month')
    year = django_filters.NumberFilter(field_name="date", lookup_expr='year')
    
    class Meta:
        model = Spending
        fields = ['category', 'date', 'month', 'year', 'spent_for', 'min_amount', 'max_amount' ]