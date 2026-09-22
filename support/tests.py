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
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status,'open')
    def test_other_user_cannot_reply(self):
        self.client.force_login(self.other)
        response=self.client.post(reverse('ticket_reply',args=[self.ticket.pk]),{'body':'intrusion'})
        self.assertEqual(response.status_code,404)
        self.assertFalse(TicketMessage.objects.filter(body='intrusion').exists())

    def test_ticket_list_is_paginated(self):
        self.client.force_login(self.owner)
        for i in range(24):
            Ticket.objects.create(user=self.owner,subject=f'Ticket {i}',body='Body')
        response=self.client.get(reverse('tickets'))
        self.assertEqual(len(response.context['tickets']),20)
        second=self.client.get(reverse('tickets')+'?page=2')
        self.assertEqual(len(second.context['tickets']),5)

    def test_duplicate_active_ticket_subject_is_rejected(self):
        self.client.force_login(self.owner)
        response=self.client.post(reverse('tickets'),{'subject':'Help','body':'Duplicate'},follow=True)
        self.assertEqual(Ticket.objects.filter(user=self.owner,subject='Help').count(),1)
        self.assertContains(response,'یک درخواست باز با همین موضوع دارید')

    def test_resolved_ticket_rejects_customer_reply(self):
        self.ticket.status='resolved'
        self.ticket.save(update_fields=['status'])
        self.client.force_login(self.owner)
        response=self.client.post(reverse('ticket_reply',args=[self.ticket.pk]),{'body':'reopen'})
        self.assertEqual(response.status_code,302)
        self.assertFalse(TicketMessage.objects.filter(ticket=self.ticket,body='reopen').exists())
