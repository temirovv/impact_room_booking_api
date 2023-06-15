from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from .models import Room
from .serializers import RoomSerializer


class RoomDetailTest(APITestCase):
    def setUp(self):
        self.room = Room.objects.create(name="Room test1", room_type='conference', capacity=5)

    def test_existing_room(self):
        url = reverse('room-detail', args=[self.room.pk])
        response = self.client.get(url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, RoomSerializer(self.room).data)

    def test_nonexisting_room(self):
        url = reverse('room-detail', args=[1000])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {"error": "topilmadi"})
