from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Sum
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404

from tracker.filters import BudgetFilter, SpendingFilter, ToBuyItemFilter
from .models import Budget, Category, Spending, ToBuyItem
from .serializers import BudgetSerializer, BuyItemSerializer, CategorySerializer, SpendingSerializer, ToBuyItemSerializer

# ViewSets for Spendings and ToBuyItems

class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

# The SpendingViewSet allows users to perform CRUD operations on their spendings - calculate a score based on filters and get a summary by category.
class SpendingViewSet(viewsets.ModelViewSet):
    serializer_class = SpendingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = SpendingFilter

    def get_queryset(self):
        return Spending.objects.filter(owner=self.request.user).order_by('-date')
    
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
        summary = self.get_queryset().values('category__name').annotate(
            total_spent=Sum('amount'),
            items_count=Count('id')
        ).order_by('-total_spent')

        return Response(summary)
    
    @action(detail=False, methods=['get'])
    def summary_by_spent_for(self, request): 
        summary = self.get_queryset().values('spent_for').annotate(
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
        return ToBuyItem.objects.filter(owner=self.request.user)

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
                    spent_for=item.tobuy_for
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
        return Budget.objects.filter(owner=self.request.user).order_by('-year', '-month')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'])
    def categories_and_spent_for_choices(self, request):
        categories = Category.objects.filter(owner=request.user).values_list('name', flat=True)
        return Response({
            "categories": list(categories),
            "spent_for_choices": [c[0] for c in Spending.SpentForChoices.choices]
        })
    
    @action(detail=False, methods=['get'])
    def budgets_detailed_report(self, request):
        queryset = self.get_queryset()

        filterset = BudgetFilter(request.GET, queryset=queryset)
        
        if not filterset.is_valid():
            return Response(filterset.errors, status=status.HTTP_400_BAD_REQUEST)
        
        filtered_qs = filterset.qs

        # Generate the report for each budget entry
        report = []
        for budget in filtered_qs:
            total_spent = Spending.objects.filter(
                owner=request.user,
                category=budget.category,
                spent_for=budget.spent_for,
                date__month=budget.month,
                date__year=budget.year
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            report.append({
                "category": budget.category.name if budget.category else "No Category",
                "spent_for": budget.get_spent_for_display() if budget.spent_for else "No Spent For",
                "month": budget.month,
                "year": budget.year,
                "budgeted_amount": budget.amount,
                "total_spent": total_spent,
                "remaining_budget": budget.amount - total_spent
            })

        return Response(report)
        
    @action(detail=False, methods=['get'])
    def monthly_summary(self, request):
        queryset = self.get_queryset()

        filterset = BudgetFilter(request.GET, queryset=queryset)
        
        if not filterset.is_valid():
            return Response(filterset.errors, status=status.HTTP_400_BAD_REQUEST)
        
        filtered_qs = filterset.qs

        summary_month = {}
        for budget in filtered_qs:
            key = f"{budget.month}/{budget.year}"
            if key not in summary_month:
                summary_month[key] = {
                    "month": budget.month,
                    "year": budget.year,
                    "total_budgeted": 0,
                    "total_spent": 0
                }
            summary_month[key]["total_budgeted"] += budget.amount
            
            total_spent = Spending.objects.filter(
                owner=request.user,
                category=budget.category,
                spent_for=budget.spent_for,
                date__month=budget.month,
                date__year=budget.year
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            summary_month[key]["total_spent"] += total_spent

        return Response(list(summary_month.values()))
    
    @action(detail=False, methods=['get'])
    def yearly_summary(self, request):
        queryset = self.get_queryset()

        filterset = BudgetFilter(request.GET, queryset=queryset)
        
        if not filterset.is_valid():
            return Response(filterset.errors, status=status.HTTP_400_BAD_REQUEST)
        
        filtered_qs = filterset.qs

        summary_year = {}
        for budget in filtered_qs:
            key = f"{budget.year}"
            if key not in summary_year:
                summary_year[key] = {
                    "year": budget.year,
                    "total_budgeted": 0,
                    "total_spent": 0
                }
            summary_year[key]["total_budgeted"] += budget.amount
            
            total_spent = Spending.objects.filter(
                owner=request.user,
                category=budget.category,
                spent_for=budget.spent_for,
                date__year=budget.year
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            summary_year[key]["total_spent"] += total_spent

        return Response(list(summary_year.values()))
    
    @action(detail=False, methods=['get'])
    def category_summary(self, request):
        queryset = self.get_queryset()

        filterset = BudgetFilter(request.GET, queryset=queryset)
        
        if not filterset.is_valid():
            return Response(filterset.errors, status=status.HTTP_400_BAD_REQUEST)
        
        filtered_qs = filterset.qs

        summary_category = {}
        for budget in filtered_qs:
            key = budget.category.name if budget.category else "No Category"
            if key not in summary_category:
                summary_category[key] = {
                    "category": key,
                    "total_budgeted": 0,
                    "total_spent": 0
                }
            summary_category[key]["total_budgeted"] += budget.amount
            
            total_spent = Spending.objects.filter(
                owner=request.user,
                category=budget.category,
                spent_for=budget.spent_for,
                date__month=budget.month,
                date__year=budget.year
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            summary_category[key]["total_spent"] += total_spent

        return Response(list(summary_category.values()))
    
    @action(detail=False, methods=['get'])
    def spent_for_summary(self, request):
        queryset = self.get_queryset()

        filterset = BudgetFilter(request.GET, queryset=queryset)
        
        if not filterset.is_valid():
            return Response(filterset.errors, status=status.HTTP_400_BAD_REQUEST)
        
        filtered_qs = filterset.qs

        summary_spent_for = {}
        for budget in filtered_qs:
            key = budget.get_spent_for_display() if budget.spent_for else "No Spent For"
            if key not in summary_spent_for:
                summary_spent_for[key] = {
                    "spent_for": key,
                    "total_budgeted": 0,
                    "total_spent": 0
                }
            summary_spent_for[key]["total_budgeted"] += budget.amount
            
            total_spent = Spending.objects.filter(
                owner=request.user,
                category=budget.category,
                spent_for=budget.spent_for,
                date__month=budget.month,
                date__year=budget.year
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            summary_spent_for[key]["total_spent"] += total_spent

        return Response(list(summary_spent_for.values()))
    
    @action(detail=False, methods=['get'])
    def overall_summary(self, request):
        queryset = self.get_queryset()

        filterset = BudgetFilter(request.GET, queryset=queryset)
        
        if not filterset.is_valid():
            return Response(filterset.errors, status=status.HTTP_400_BAD_REQUEST)
        
        filtered_qs = filterset.qs

        total_budgeted = filtered_qs.aggregate(total=Sum('amount'))['total'] or 0
        
        total_spent = 0
        for budget in filtered_qs:
            spent = Spending.objects.filter(
                owner=request.user,
                category=budget.category,
                spent_for=budget.spent_for,
                date__month=budget.month,
                date__year=budget.year
            ).aggregate(total=Sum('amount'))['total'] or 0
            total_spent += spent

        return Response({
            "total_budgeted": total_budgeted,
            "total_spent": total_spent,
            "remaining_budget": total_budgeted - total_spent
        })
    