from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Sum
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404

from tracker.filters import SpendingFilter, ToBuyItemFilter
from .models import Spending, ToBuyItem
from .serializers import BuyItemSerializer, SpendingSerializer, ToBuyItemSerializer

# ViewSets for Spendings and ToBuyItems

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