from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BudgetViewSet, CategoryViewSet, SpendingViewSet, ToBuyItemViewSet

router = DefaultRouter()
router.register(r'spendings', SpendingViewSet, basename='spending')
router.register(r'tobuyitems',ToBuyItemViewSet, basename='tobuyitems')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'budgets', BudgetViewSet, basename='budget')

urlpatterns = [
    path('', include(router.urls)),
]