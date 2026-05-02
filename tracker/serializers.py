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
    owner = serializers.ReadOnlyField(source='owner.username')

    category_name = serializers.CharField(write_only=True, required=True)
    category = CategorySerializer(read_only=True)
    
    class Meta:
        model = Spending
        fields = [
            'id', 'owner', 'amount', 'date', 'title',
            'category_name', 'category'
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
    owner = serializers.ReadOnlyField(source='owner.username')
    
    category_name = serializers.CharField(write_only=True, required=True)
    category = CategorySerializer(read_only=True)
    
    class Meta:
        model = ToBuyItem
        fields = [
            'id', 'owner', 'title', 'category', 'category_name'
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
    
    budget_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    actual_spent = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    category = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Category.objects.all(),
        required=False, allow_null=True,
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
        fields = ['id', 'owner', 'category', 'actual_spent', 'budget_amount', 'month', 'year']
    
    def validate(self, data):
        owner = self.context['request'].user
        category = data.get('category')
        month = data.get('month')
        year = data.get('year')

        
        if category and category.owner != owner:
            raise serializers.ValidationError("You don't have a category with that name. Please create the category first or choose an existing one.")
        
        now = datetime.datetime.now()
        if year < now.year or (year == now.year and month < now.month):
            raise serializers.ValidationError("Month and year must be in the future.")

        budget = Budget.objects.filter(
            owner=owner,
            category=category,
            month=month,
            year=year
        )
        # Exclude the current instance from the uniqueness check when updating an existing budget. This allows users to update a budget without triggering a validation error about duplicate budgets.
        if self.instance:
            budget = budget.exclude(id=self.instance.id)

        if budget.exists():
            raise serializers.ValidationError(
                "A budget for this already exists."
            )
        
        return data
