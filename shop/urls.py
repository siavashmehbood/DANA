from django.urls import path
from .bank import bank_checkout, payment_callback
from .views import cart, checkout, order_detail, remove_cart_item, wallet, orders, subscriptions

urlpatterns = [
    path('cart/', cart, name='cart'),
    path('cart/remove/<int:pk>/', remove_cart_item, name='cart_remove'),
    path('checkout/', checkout, name='checkout'),
    path('bank-checkout/', bank_checkout, name='bank_checkout'),
    path('payment/callback/', payment_callback, name='payment_callback'),
    path('subscriptions/', subscriptions, name='subscriptions'),
    path('orders/', orders, name='orders'),
    path('orders/<str:tracking_code>/', order_detail, name='order_detail'),
    path('wallet/', wallet, name='wallet'),
]
