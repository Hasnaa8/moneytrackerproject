from rest_framework import serializers
from .models import Spending, ToBuyItem

class SpendingSerializer(serializers.ModelSerializer):
    # We display the label (e.g., "For Self") instead of just the code ("SELF")
    spent_for_display = serializers.CharField(source='get_spent_for_display', read_only=True)
    owner = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = Spending
        fields = [
            'id', 'owner', 'amount', 'date', 'title',
            'category', 'spent_for', 'spent_for_display'
        ]

class ToBuyItemSerializer(serializers.ModelSerializer):
    # We display the label (e.g., "For Self") instead of just the code ("SELF")
    tobuy_for_display = serializers.CharField(source='get_tobuy_for_display', read_only=True)
    owner = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = ToBuyItem
        fields = [
            'id', 'owner', 'title', 'category', 'tobuy_for', 'tobuy_for_display'
        ]


class BuyItemSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)