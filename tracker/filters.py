import django_filters
from .models import Spending, ToBuyItem

class SpendingFilter(django_filters.FilterSet):
    min_amount = django_filters.NumberFilter(field_name="amount", lookup_expr='gte')
    max_amount = django_filters.NumberFilter(field_name="amount", lookup_expr='lte')
    
    min_date = django_filters.DateFilter(field_name="date", lookup_expr='gte')
    max_date = django_filters.DateFilter(field_name="date", lookup_expr='lte')

    month = django_filters.NumberFilter(field_name="date", lookup_expr='month')
    year = django_filters.NumberFilter(field_name="date", lookup_expr='year')
    
    spent_for = django_filters.CharFilter(field_name='spent_for', lookup_expr='icontains')
    category = django_filters.CharFilter(field_name='category', lookup_expr='icontains')

    class Meta:
        model = Spending
        fields = ['category', 'date', 'spent_for']

class ToBuyItemFilter(django_filters.FilterSet):
    tobuy_for = django_filters.CharFilter(field_name='tobuy_for', lookup_expr='icontains')
    category = django_filters.CharFilter(field_name='category', lookup_expr='icontains')
    class Meta:
        model = ToBuyItem
        fields = ['category', 'tobuy_for']
        