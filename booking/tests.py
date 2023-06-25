from datetime import datetime
from datetime import date

from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone
from django.urls import reverse
from django.conf import settings

from .models import Room, Booking, Resident
from .serializers import RoomSerializer


class RoomListTest(APITestCase):
    def setUp(self):
        self.room = Room.objects.create(name='training room', room_type='conference', capacity=9)
        self.params = {'name': 'training room', 'type': 'conference'}
        self.url = reverse('rooms')

    def test_get_available_rooms(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        
        assert 'page' in data
        assert 'count' in data
        assert 'page_size' in data
        assert 'results' in data

        results = data['results']
        assert isinstance(results, list)
        assert len(results) >= 1, "kamida bitta xona bo'lishi kerak (id=1)"

        for room in results:
            assert 'id' in room
            assert 'name' in room
            assert 'room_type' in room
            assert 'capacity' in room

    def test_get_available_rooms_with_search(self)    :
        url = self.url
        url += f"?name={self.params['name']}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['name'], self.params['name'])
        
    def test_get_rooms_with_filter(self):
        url = self.url
        url += f"?room_type={self.params['type']}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
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
        self.resident = Resident.objects.create(name="Residentjon")
        self.url = reverse('room-booking', args=[self.room.pk])

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

    def test_invalid_booking_data(self):
        invalid_data = self.booking.copy()
        invalid_data['resident']['name'] = ''

        response = self.client.post(self.url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'Resident nomi bo‘sh bo‘lishi mumkin emas'})

    def test_book_room_successfully(self):
        response = self.client.post(self.url, data=self.booking, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {'message': 'xona muvaffaqiyatli band qilindi'}) 

    def test_book_room_busy(self):
        booked_room = Booking.objects.create(
            room=self.room, 
            resident=self.resident,
            start = datetime.strptime(self.booking['start'], settings.DATETIME_FORMAT),
            end = datetime.strptime(self.booking['end'], settings.DATETIME_FORMAT)
        )
        response = self.client.post(self.url, self.booking, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        self.assertEqual(response.data, {'error': 'uzr, siz tanlagan vaqtda xona band'})

    def test_valid_and_invalid_booking(self):
        # valid booking
        response = self.client.post(self.url, data=self.booking, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {'message': 'xona muvaffaqiyatli band qilindi'})    
        
        booking = Booking.objects.last()
        self.assertEqual(booking.room, self.room)
        self.assertEqual(booking.resident.name, self.booking['resident']['name'])
        # invalid booking
        response = self.client.post(self.url, data=self.booking, format='json')

        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        self.assertEqual(response.data, {'error': 'uzr, siz tanlagan vaqtda xona band'})


class RoomAvailabiltyTest(APITestCase):
    def setUp(self):
        self.room = Room.objects.create(name='traning room', room_type='focus', capacity=9)
        self.resident = Resident.objects.create(name="Residentjon")
        self.url = reverse('availability', args=[self.room.pk])

    def test_get_room_availability_today(self):
        response = self.client.get(self.url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assert isinstance(response.data, list), "qabul qilingan ma'lumot list tipida bo'lishi kerak"
        assert len(response.data) >= 1, "ro'yhatda kamida bitta element bo'lishi kerak"

    def test_get_room_availability_specific_date(self):
        url = self.url
        date_ = "2023-06-30"
        url += f"?search={date_}"

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assert isinstance(response.data, list), "qabul qilingan ma'lumot list tipida bo'lishi kerak"
        assert len(response.data) >= 1, "ro'yhatda kamida bitta element bo'lishi kerak"

    def test_get_room_updated_availability_specific_date(self):
        self.booked_room = Booking.objects.create(
            room=self.room, 
            resident=self.resident,
            start = datetime.strptime('30-06-2023 10:00:00', settings.DATETIME_FORMAT),
            end = datetime.strptime('30-06-2023 11:00:00', settings.DATETIME_FORMAT)
        )
        date_ = "2023-06-30"

        url = self.url
        url += f"?search={date_}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assert isinstance(response.data, list), "qabul qilingan ma'lumot list tipida bo'lishi kerak"
        assert len(response.data) >= 2, "ro'yhatda kamida ikta element bo'lishi kerak"
        
