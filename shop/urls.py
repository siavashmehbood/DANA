from django.urls import path
from .views import cart, checkout, order_detail, remove_cart_item, wallet

urlpatterns = [
    path('cart/', cart, name='cart'),
    path('cart/remove/<int:pk>/', remove_cart_item, name='cart_remove'),
    path('checkout/', checkout, name='checkout'),
    path('orders/<str:tracking_code>/', order_detail, name='order_detail'),
    path('wallet/', wallet, name='wallet'),
]
