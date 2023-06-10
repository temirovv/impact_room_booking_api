from django.urls import path
from .views import RoomListAPIView, RoomDetailView, BookingRoomView, RoomAvailabiltyAPIView


urlpatterns = [
    path('', RoomListAPIView.as_view()),
    path('<int:pk>/', RoomDetailView.as_view()),
    path("<int:pk>/book/", BookingRoomView.as_view()),
    path("<int:pk>/availability/", RoomAvailabiltyAPIView.as_view()),
]
