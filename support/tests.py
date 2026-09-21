from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from .models import Ticket, TicketMessage

class SupportFlowTests(TestCase):
    def setUp(self):
        self.owner=User.objects.create_user(username='ticket-owner',password='pass12345')
        self.other=User.objects.create_user(username='ticket-other',password='pass12345')
        self.ticket=Ticket.objects.create(user=self.owner,subject='Help',body='Initial')
    def test_owner_can_reply(self):
        self.client.force_login(self.owner)
        response=self.client.post(reverse('ticket_reply',args=[self.ticket.pk]),{'body':'More details'})
        self.assertEqual(response.status_code,302)
        self.assertTrue(TicketMessage.objects.filter(ticket=self.ticket,user=self.owner,body='More details').exists())
    def test_other_user_cannot_reply(self):
        self.client.force_login(self.other)
        response=self.client.post(reverse('ticket_reply',args=[self.ticket.pk]),{'body':'intrusion'})
        self.assertEqual(response.status_code,404)
        self.assertFalse(TicketMessage.objects.filter(body='intrusion').exists())
