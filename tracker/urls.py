from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SpendingViewSet, ToBuyItemViewSet

router = DefaultRouter()
router.register(r'spendings', SpendingViewSet, basename='spending')
router.register(r'tobuyitems',ToBuyItemViewSet, basename='tobuyitems')

urlpatterns = [
    path('', include(router.urls)),
]