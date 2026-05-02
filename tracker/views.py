from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import F, Count, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404

from tracker.filters import BudgetFilter, SpendingFilter, ToBuyItemFilter
from .models import Budget, Category, Spending, ToBuyItem
from .serializers import BudgetSerializer, BuyItemSerializer, CategorySerializer, SpendingSerializer, ToBuyItemSerializer
from tracker import models

# ViewSets for Spendings and ToBuyItems

class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(owner=self.request.user).select_related('owner')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

# The SpendingViewSet allows users to perform CRUD operations on their spendings - calculate a score based on filters and get a summary by category.
class SpendingViewSet(viewsets.ModelViewSet):
    serializer_class = SpendingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = SpendingFilter

    def get_queryset(self):
        return Spending.objects.filter(owner=self.request.user).select_related('owner', 'category').order_by('-date')
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'])
    def calculate_score(self, request):
        queryset = self.get_queryset()

        filterset = SpendingFilter(request.GET, queryset=queryset)
        
        if not filterset.is_valid():
            return Response(filterset.errors, status=status.HTTP_400_BAD_REQUEST)
        
        filtered_qs = filterset.qs

        total_score = filtered_qs.aggregate(total=Sum('amount'))['total'] or 0
        
        return Response({
            "count": filtered_qs.count(),
            "total_score": total_score,
            "filters_applied": request.GET 
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def summary_by_category(self, request):
        queryset = self.get_queryset()

        filterset = SpendingFilter(request.GET, queryset=queryset)
        
        if not filterset.is_valid():
            return Response(filterset.errors, status=status.HTTP_400_BAD_REQUEST)
        
        filtered_qs = filterset.qs

        summary = filtered_qs.values('category__name').annotate(
            total_spent=Sum('amount'),
            items_count=Count('id')
        ).order_by('-total_spent')

        return Response(summary)
    
# The ToBuyItemViewSet allows users to manage their to-buy items.
class ToBuyItemViewSet(viewsets.ModelViewSet):
    serializer_class = ToBuyItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = ToBuyItemFilter

    def get_queryset(self):
        return ToBuyItem.objects.filter(owner=self.request.user).select_related('owner', 'category').order_by('-id')
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'], serializer_class=BuyItemSerializer)
    def buy(self, request, pk=None):
        queryset = self.get_queryset()
        item = get_object_or_404(queryset, pk=pk)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data.get('amount')
        
        date_of_purchase = request.data.get('date', timezone.now().date())
        
        try:
            with transaction.atomic():
                item_name = item.title if item.title else "Unnamed Item"
                Spending.objects.create(
                    owner=item.owner,
                    category=item.category,
                    title=item_name,
                    amount=amount,
                    date=date_of_purchase,
                )
                item.delete()
                
            return Response(
                {"message": f"Successfully purchased '{item_name}' for {amount} on {date_of_purchase}. Item has been moved to your spending list."},
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {"error": "Please try again. An unexpected error occurred."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = BudgetFilter

    def get_queryset(self):
        return Budget.objects.filter(
            owner=self.request.user
        ).select_related('category').order_by('-year', '-month', 'category__name')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'])
    def categorieschoices(self, request):
        categories = Category.objects.filter(owner=request.user).values_list('name', flat=True)
        return Response({
            "categories": list(categories),
        })
    
    @action(detail=False, methods=['get'])
    def budgets_detailed_report(self, request):

        filtered_qs = self.filter_queryset(self.get_queryset())

        # Generate the report for each budget entry
        report = []
        for budget in filtered_qs:
            
            report.append({
                "category": budget.category.name if budget.category else "No Category",
                "month": budget.month,
                "year": budget.year,
                "budgeted_amount": budget.budget_amount,
                "total_spent": budget.actual_spent,
                "remaining_budget": budget.budget_amount - budget.actual_spent
            })

        return Response(report)
        
    @action(detail=False, methods=['get'])
    def monthly_summary(self, request):
        filtered_qs = self.filter_queryset(self.get_queryset())
        
        summary_month = filtered_qs.values('year', 'month').annotate(
            total_budgeted=Sum('budget_amount'),
            total_spent=Sum('actual_spent')
        ).order_by('-year', '-month')

        return Response(list(summary_month.values()))
    
    @action(detail=False, methods=['get'])
    def yearly_summary(self, request):
        filtered_qs = self.filter_queryset(self.get_queryset())
        
        summary_year = filtered_qs.values('year').annotate(
            total_budgeted=Sum('budget_amount'),
            total_spent=Sum('actual_spent')
        ).order_by('-year')

        return Response(list(summary_year.values()))
    
    @action(detail=False, methods=['get'])
    def category_summary(self, request):
        filtered_qs = self.filter_queryset(self.get_queryset())
        
        summary_category = filtered_qs.values(
            category_name=F('category__name')).annotate(   
                total_budgeted=Sum('budget_amount'),
                total_spent=Sum('actual_spent')
            )

        return Response(list(summary_category.values()))
    

    @action(detail=False, methods=['get'])
    def overall_summary(self, request):
        filtered_qs = self.filter_queryset(self.get_queryset())
        summary = filtered_qs.aggregate(
            total_budgeted=Sum('budget_amount'),
            total_spent=Sum('actual_spent')
        )
        
        return Response({
            "total_budgeted": summary['total_budgeted'],
            "total_spent": summary['total_spent'],
            "remaining_budget": summary['total_budgeted'] - summary['total_spent']
        })
    