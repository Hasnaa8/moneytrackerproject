from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import Spending, ToBuyItem
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from .serializers import SpendingSerializer, ToBuyItemSerializer

class SpendingViewSet(viewsets.ModelViewSet):
    serializer_class = SpendingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 🔒 Privacy: Users only see their own expenses
        return Spending.objects.filter(owner=self.request.user).order_by('-date')

    def perform_create(self, serializer):
        # 🔑 Security: Automatically set the owner to the logged-in user
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'])
    def calculate_score(self, request):
        """
        Dynamic calculator based on user choice.
        URL Examples:
        - /api/expenses/calculate_score/?year=2026
        - /api/expenses/calculate_score/?date=2026-04-10&spent_for=HOME
        - /api/expenses/calculate_score/?month=4&year=2026
        """
        queryset = self.get_queryset()

        # 1. Filter by Date (Specific Day)
        date_param = request.query_params.get('date')
        if date_param:
            queryset = queryset.filter(date=date_param)

        # 2. Filter by Month/Year
        month_param = request.query_params.get('month')
        year_param = request.query_params.get('year')
        if month_param:
            queryset = queryset.filter(date__month=month_param)
        if year_param:
            queryset = queryset.filter(date__year=year_param)
        
        # 3. Filter by 'Spent For' (If the user chose one)
        spent_for_param = request.query_params.get('spent_for')
        if spent_for_param:
            queryset = queryset.filter(spent_for=spent_for_param)

        # 4. Calculate the final score
        total_score = queryset.aggregate(Sum('amount'))['amount__sum'] or 0

        return Response({
            "filters_applied": {
                "date": date_param,
                "month": month_param,
                "year": year_param,
                "spent_for": spent_for_param
            },
            "total_count": queryset.count(),
            "total_score": total_score
        })


class ToBuyItemViewSet(viewsets.ModelViewSet):
    serializer_class = ToBuyItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 🔒 Privacy: Users only see their own expenses
        return ToBuyItem.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        # 🔑 Security: Automatically set the owner to the logged-in user
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def buy(self, request, pk=None):
        """
        Dynamic calculator based on user choice.
        URL Examples:
        - /api/expenses/calculate_score/?year=2026
        - /api/expenses/calculate_score/?date=2026-04-10&spent_for=HOME
        - /api/expenses/calculate_score/?month=4&year=2026
        """
        queryset = self.get_queryset()
        item = get_object_or_404(queryset, pk=pk)
        
        # استلام البيانات من المستخدم (السعر هو الأهم هنا)
        amount = request.data.get('amount')
        # إذا لم يرسل تاريخاً، نستخدم تاريخ اليوم تلقائياً
        date_of_purchase = request.data.get('date', timezone.now().date())

        if not amount:
            return Response(
                {"error": "يجب إدخال المبلغ (amount) لإتمام العملية"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # 1. إنشاء السجل في جدول النفقات (Expense/Transaction)
                Spending.objects.create(
                    owner=item.owner,
                    category=item.category,
                    amount=amount,
                    date=date_of_purchase,
                    spent_for=item.tobuy_for
                )
                
                # 2. حذف العنصر من قائمة التسوق (Wishlist/PlannedItem)
                item.delete()
                
            return Response(
                {"message": f"تم شراء '{item.category}' بنجاح ونقله إلى النفقات"}, 
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            # يمكنك طباعة الخطأ في الـ logs لمعرفته
            return Response(
                {"error": "فشلت العملية، يرجى المحاولة مرة أخرى"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )