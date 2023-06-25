from datetime import datetime
from datetime import date

from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone
from django.urls import reverse

from .models import Room, Booking
from .serializers import RoomSerializer


class RoomListTest(APITestCase):
    def setUp(self):
        self.room = Room.objects.create(name='training room', room_type='conference', capacity=9)
        self.params = {'name': 'training room', 'type': 'conference'}

    def test_get_rooms_with_filter_by_name(self):
        url = reverse('rooms')
        url += f"?name={self.params['name']}&room_type="
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['name'], self.params['name'])
        
    def test_get_rooms_with_filter_by_room_type(self):
        url = reverse('rooms')
        url += f"?name=&room_type={self.params['type']}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['room_type'], self.params['type'])

    def test_get_rooms_with_filter(self):
        url = reverse('rooms')
        url += f"?name={self.params['name']}&room_type={self.params['type']}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['name'], self.params['name'])
        self.assertEqual(response.data['results'][0]['room_type'], self.params['type'])


class RoomDetailTest(APITestCase):
    def setUp(self):
        self.room = Room.objects.create(name='Room test1', room_type='conference', capacity=5)
        
    def test_get_room_by_id_existing(self):
        url = reverse('room-detail', args=[self.room.pk])
        response = self.client.get(url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, RoomSerializer(self.room).data)

    def test_nonexisting_room(self):
        url = reverse('room-detail', args=[1000])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'error': 'topilmadi'})


class BookingRoom(APITestCase):
    def setUp(self):
        self.room = Room.objects.create(name='traning room', room_type='focus', capacity=9)
        today = timezone.localdate()
        
        day, month, year = today.day, today.month, today.year
        try:
            booking_date = date(day=day+1, month=month, year=year).strftime('%d-%m-%Y')
        except ValueError:
            booking_date = date(year=year, month=month+1, day=1)
        
        booking_date = str(booking_date)
        self.booking = {
            "resident": {"name": "Residentjon"},
            "start": f"{booking_date} 09:00:00",
            "end": f"{booking_date} 11:00:00"
        }

    def tearDown(self):
        pass

    def test_invalid_booking_data(self):
        url = reverse('room-booking', args=[self.room.pk])
        invalid_data = self.booking.copy()
        invalid_data['resident']['name'] = ''

        response = self.client.post(url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'Resident nomi bo‘sh bo‘lishi mumkin emas'})

    def test_valid_and_invalid_booking(self):
        url = reverse('room-booking', args=[self.room.pk])
        # valid booking
        response = self.client.post(url, data=self.booking, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {'message': 'xona muvaffaqiyatli band qilindi'})    
        
        booking = Booking.objects.last()
        self.assertEqual(booking.room, self.room)
        self.assertEqual(booking.resident.name, self.booking['resident']['name'])
        # invalid booking
        response = self.client.post(url, data=self.booking, format='json')

        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        self.assertEqual(response.data, {'error': 'uzr, siz tanlagan vaqtda xona band'})
