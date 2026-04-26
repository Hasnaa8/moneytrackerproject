from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Sum
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404

from tracker.filters import SpendingFilter
from .models import Spending, ToBuyItem
from .serializers import SpendingSerializer, ToBuyItemSerializer

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
        # 1. Get the base queryset (only the user's spending)
        queryset = self.get_queryset()

        # 2. Apply the SpendingFilter
        filterset = SpendingFilter(request.GET, queryset=queryset)
        
        if not filterset.is_valid():
            return Response(filterset.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # 3. Get the "Filtered" queryset
        filtered_qs = filterset.qs

        # 4. PERFORM THE CALCULATION
        total_score = filtered_qs.aggregate(total=Sum('amount'))['total'] or 0
        
        # 5. Return the result
        return Response({
            "count": filtered_qs.count(),
            "total_score": total_score,
            "filters_applied": request.GET  # Useful for the frontend to confirm
        }, status=status.HTTP_200_OK)
        
    @action(detail=False, methods=['get'])
    def summary_by_category(self, request):
        summary = self.get_queryset().values('category').annotate(
            total_spent=Sum('amount'),
            items_count=Count('id')
        ).order_by('-total_spent')

        return Response(summary)


class ToBuyItemViewSet(viewsets.ModelViewSet):
    serializer_class = ToBuyItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ToBuyItem.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def buy(self, request, pk=None):
        queryset = self.get_queryset()
        item = get_object_or_404(queryset, pk=pk)
        
        amount = request.data.get('amount')
        date_of_purchase = request.data.get('date', timezone.now().date())

        if not amount:
            return Response(
                {"error": "يجب إدخال المبلغ (amount)"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response({"error": "يرجى إدخال مبلغ صحيح وأكبر من الصفر"}, status=400)
        try:
            with transaction.atomic():
                Spending.objects.create(
                    owner=item.owner,
                    category=item.category,
                    amount=amount,
                    date=date_of_purchase,
                    spent_for=item.tobuy_for
                )
                
                item.delete()
                
            return Response(
                {"message": f"تم شراء '{item.category}'"}, 
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {"error": "يرجى المحاولة مرة أخرى"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )