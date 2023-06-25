from django.urls import path
from .views import RoomListAPIView, RoomDetailView, BookingRoomView, RoomAvailabiltyAPIView


urlpatterns = [
    path('', RoomListAPIView.as_view(), name='rooms'),
    path('<int:pk>/', RoomDetailView.as_view(), name='room-detail'),
    path("<int:pk>/book/", BookingRoomView.as_view(), name='room-booking'),
    path("<int:pk>/availability/", RoomAvailabiltyAPIView.as_view(), name='availability'),
]
