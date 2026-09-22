import json
from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from analytics.models import Event

class EventApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='api-user', password='pass12345')
        self.url = reverse('api_event')
        self.client.login(username='api-user', password='pass12345')

    def test_event_accepts_object_payload(self):
        response = self.client.post(self.url, data=json.dumps({'name': 'reader_opened', 'metadata': {'book_id': 3}}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Event.objects.get().name, 'reader_opened')

    def test_event_rejects_malformed_json(self):
        response = self.client.post(self.url, data='{', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'invalid_json')
        self.assertFalse(Event.objects.exists())

    def test_event_rejects_non_object_metadata(self):
        response = self.client.post(self.url, data=json.dumps({'name': 'bad', 'metadata': []}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'metadata_object_required')
        self.assertFalse(Event.objects.exists())

    def test_event_rejects_invalid_name(self):
        response = self.client.post(self.url, data=json.dumps({'name': ''}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'invalid_name')


    def test_event_rejects_unknown_client_event(self):
        response = self.client.post(self.url, data=json.dumps({'name': 'made_up_metric'}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'unsupported_event')
        self.assertFalse(Event.objects.exists())
