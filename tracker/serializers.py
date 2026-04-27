import datetime

from rest_framework import serializers

from tracker.validators import validate_maximum_categories
from .models import Budget, Category, Spending, ToBuyItem

# Serializers for the tracker app

# The CategorySerializer is used to serialize and validate Category instances.
class CategorySerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
 
    class Meta:
        model = Category
        fields = ['id', 'owner', 'name']
    
    # Validate that the user does not exceed the maximum number of categories when creating a new one.
    def validate(self, data):
        owner = self.context['request'].user
        if self.instance is None:  # Only validate when creating a new
            if Category.objects.filter(owner=owner).count() >= 10:
                raise serializers.ValidationError("Maximum category limit reached.")
        return data

# The SpendingSerializer is used to serialize and validate Spending instances.
class SpendingSerializer(serializers.ModelSerializer):
    spent_for_display = serializers.CharField(source='get_spent_for_display', read_only=True)
    owner = serializers.ReadOnlyField(source='owner.username')

    category_name = serializers.CharField(write_only=True, required=False)
    category = CategorySerializer(read_only=True)
    
    class Meta:
        model = Spending
        fields = [
            'id', 'owner', 'amount', 'date', 'title',
            'category_name', 'category', 'spent_for', 'spent_for_display'
        ]
    
    # Validate that the user does not exceed the maximum number of categories when creating a new one.
    def validate_category(self):
        if Category.objects.filter(owner=self.context['request'].user).count() > 10:
            raise serializers.ValidationError("Maximum category limit reached.")
    
    # Validate that the amount entered for a spending is a positive number..
    def validate_amount(self, amount):        
        if amount is None:
            raise serializers.ValidationError("Please enter a purchase amount.")
        if amount <= 0:
            raise serializers.ValidationError("The amount must be a positive number.")   
        return amount
    
    # to handle category creation if a category name is provided. This allows users to create a new category when creating a spending entry.
    def create(self, validated_data):
        category_name = validated_data.pop('category_name', None)
        if category_name:
            owner = self.context['request'].user
            
            category_in = Category.objects.filter(owner=owner, name=category_name).first()
            if not category_in:
                self.validate_category()
                category = Category.objects.create(owner=owner, name=category_name)
            else:
                category = category_in
            validated_data['category'] = category
        return Spending.objects.create(**validated_data)
    

class ToBuyItemSerializer(serializers.ModelSerializer):
    tobuy_for_display = serializers.CharField(source='get_tobuy_for_display', read_only=True)
    owner = serializers.ReadOnlyField(source='owner.username')
    
    category_name = serializers.CharField(write_only=True, required=False)
    category = CategorySerializer(read_only=True)
    
    class Meta:
        model = ToBuyItem
        fields = [
            'id', 'owner', 'title', 'category', 'category_name', 'tobuy_for', 'tobuy_for_display'
        ]
    
    # Validate that the user does not exceed the maximum number of categories when creating a new one.
    def validate_category(self):
        if Category.objects.filter(owner=self.context['request'].user).count() > 10:
            raise serializers.ValidationError("Maximum category limit reached.")
    
    # to handle category creation if a category name is provided. This allows users to create a new category when creating a to-buy item entry.
    def create(self, validated_data):
        category_name = validated_data.pop('category_name', None)
        if category_name:
            owner = self.context['request'].user
            category_in = Category.objects.filter(owner=owner, name=category_name).first()
            if not category_in:
                self.validate_category()
                category = Category.objects.create(owner=owner, name=category_name)
            else:
                category = category_in
            validated_data['category'] = category
        return ToBuyItem.objects.create(**validated_data)

    
class BuyItemSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

    # Validate that the amount entered for a purchase is a positive number.
    def validate_amount(self, amount):
        if amount is None:
            raise serializers.ValidationError("Please enter a purchase amount.")
        if amount <= 0:
            raise serializers.ValidationError("The amount must be a positive number.")
        return amount
    

class BudgetSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    
    category = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Category.objects.all(),
        required=False, allow_null=True
    )

    spent_for = serializers.ChoiceField(
        choices=Spending.SpentForChoices.choices, 
        required=False, allow_null=True
    )
    month = serializers.IntegerField(
        min_value=1, max_value=12, required=True,
        error_messages={"msg": "Month must be between 1 and 12."}
    )
    year = serializers.IntegerField(
        min_value=2026, max_value=2099, required=True,
        error_messages={"msg": "Year must be between 2026 and 2099."}
    )
    class Meta:
        model = Budget
        fields = ['id', 'owner', 'category', 'spent_for', 'amount', 'month', 'year']
    
    def validate(self, data):
        owner = self.context['request'].user
        category = data.get('category')
        spent_for = data.get('spent_for')
        month = data.get('month')
        year = data.get('year')

        
        if category and category.owner != owner:
            raise serializers.ValidationError("You don't have a category with that name. Please create the category first or choose an existing one.")
        
        now = datetime.datetime.now()
        if year < now.year or (year == now.year and month < now.month):
            raise serializers.ValidationError("Month and year must be in the future.")

        exists = Budget.objects.filter(
            owner=owner,
            category=category,
            spent_for=spent_for,
            month=month,
            year=year
        ).exists()

        if exists:
            raise serializers.ValidationError(
                "A budget for this already exists."
            )
        
        return data
