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
        response = self.client.post(self.url, data=json.dumps({'name': 'reader_opened', 'metadata': []}), content_type='application/json')
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


    def test_event_accepts_bounded_numeric_value(self):
        response = self.client.post(self.url, data=json.dumps({'name': 'reader_progress', 'value': 42}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Event.objects.get().value, 42)

    def test_event_rejects_non_numeric_value(self):
        response = self.client.post(self.url, data=json.dumps({'name': 'reader_progress', 'value': 'lots'}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'invalid_value')


    def test_event_records_session_attribution(self):
        response = self.client.post(self.url, data=json.dumps({'name': 'book_viewed'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Event.objects.get().session_key)


    def test_event_attribution_does_not_log_user_out(self):
        self.client.post(self.url, data=json.dumps({'name': 'book_viewed'}), content_type='application/json')
        response = self.client.post(self.url, data=json.dumps({'name': 'article_viewed'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Event.objects.count(), 2)
        self.assertTrue(all(event.user_id == self.user.id for event in Event.objects.all()))


    def test_event_rejects_oversized_metadata_field(self):
        response = self.client.post(self.url, data=json.dumps({'name': 'book_viewed', 'metadata': {'note': 'x' * 2001}}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'metadata_field_too_large')


    def test_event_rejects_too_many_metadata_fields(self):
        metadata = {str(i): i for i in range(51)}
        response = self.client.post(self.url, data=json.dumps({'name': 'book_viewed', 'metadata': metadata}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'metadata_too_many_fields')


    def test_event_rejects_oversized_payload(self):
        response = self.client.post(self.url, data=json.dumps({'name': 'book_viewed', 'metadata': {'blob': 'x' * 21000}}), content_type='application/json')
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()['error'], 'payload_too_large')


    def test_event_response_is_not_cacheable(self):
        response = self.client.post(self.url, data=json.dumps({'name': 'book_viewed'}), content_type='application/json')
        self.assertIn('no-cache', response.headers.get('Cache-Control',''))


    def test_event_requires_json_content_type(self):
        response = self.client.post(self.url, data={'name': 'book_viewed'})
        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.json()['error'], 'json_required')
