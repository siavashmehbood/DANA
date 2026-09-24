import requests
from dataclasses import dataclass
from decimal import Decimal
from django.conf import settings
from django.urls import reverse


@dataclass
class GatewayResult:
    ok: bool
    authority: str = ''
    url: str = ''
    message: str = ''


class ZarinpalGateway:
    request_url = 'https://payment.zarinpal.com/pg/v4/payment/request.json'
    verify_url = 'https://payment.zarinpal.com/pg/v4/payment/verify.json'
    start_url = 'https://payment.zarinpal.com/pg/StartPay/{authority}'

    @property
    def merchant_id(self):
        return getattr(settings, 'ZARINPAL_MERCHANT_ID', '')

    @property
    def enabled(self):
        return bool(self.merchant_id)

    @property
    def multiplier(self):
        return int(getattr(settings, 'ZARINPAL_AMOUNT_MULTIPLIER', 10))

    def amount(self, order):
        return int(Decimal(order.total) * self.multiplier)

    def request(self, order, request):
        if not self.enabled:
            return GatewayResult(False, message='درگاه بانکی هنوز پیکربندی نشده است.')
        callback = request.build_absolute_uri(reverse('payment_callback'))
        payload = {
            'merchant_id': self.merchant_id,
            'amount': self.amount(order),
            'callback_url': callback,
            'description': f'DANA order {order.tracking_code}',
            'metadata': {'mobile': getattr(order.user, 'phone', '') or '', 'email': getattr(order.user, 'email', '') or ''},
        }
        try:
            response = requests.post(self.request_url, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json().get('data') or {}
            authority = data.get('authority', '')
            if int(data.get('code', -1)) in (100, 101) and authority:
                return GatewayResult(True, authority=authority, url=self.start_url.format(authority=authority))
            return GatewayResult(False, message=str(data.get('message') or 'درخواست درگاه رد شد.'))
        except (requests.RequestException, ValueError) as exc:
            return GatewayResult(False, message=f'ارتباط با درگاه ناموفق بود: {exc}')

    def verify(self, order, payment=None):
        if not self.enabled:
            return GatewayResult(False, message='درگاه بانکی پیکربندی نشده است.')
        payment = payment or order.payments.filter(provider='zarinpal').order_by('-created_at').first()
        if not payment or payment.order_id != order.pk or payment.provider != 'zarinpal' or not payment.authority:
            return GatewayResult(False, message='شناسه تراکنش پیدا نشد.')
        if Decimal(payment.amount) != Decimal(order.total):
            return GatewayResult(False, message='مبلغ تراکنش با سفارش همخوانی ندارد.')
        payload = {'merchant_id': self.merchant_id, 'amount': self.amount(order), 'authority': payment.authority}
        try:
            response = requests.post(self.verify_url, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json().get('data') or {}
            code = int(data.get('code', -1))
            if code in (100, 101):
                return GatewayResult(True, authority=data.get('ref_id', '') or payment.authority)
            return GatewayResult(False, authority=data.get('ref_id', '') or '', message=str(data.get('message') or 'پرداخت تأیید نشد.'))
        except (requests.RequestException, ValueError) as exc:
            return GatewayResult(False, message=f'تأیید پرداخت ناموفق بود: {exc}')


def gateway():
    return ZarinpalGateway()
