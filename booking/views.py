from datetime import datetime
from django.utils import timezone
from django.conf import settings
from zoneinfo import ZoneInfo
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination
from .models import Room, Resident, Booking
from .serializers import RoomSerializer, BookingSerializer, BookingRoomSerializer 


class CustomPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 10
    page_size_query_param = 'page_size'

    def get_paginated_response(self, data):
        return Response(
            {
                'page': self.page.number,
                'count': self.page.paginator.count,
                "page_size": self.page.paginator.per_page,
                # 'next': self.get_next_link(),
                # 'previous': self.get_previous_link(),
                'results': data
            }
        )


class RoomListAPIView(ListAPIView):
    queryset = Room.objects.all()
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fileds = ['type__type']
    pagination_class = CustomPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        
        search_term = self.request.query_params.get("search")
        if search_term:
            queryset = queryset.filter(name__icontains=search_term)

        room_type = self.request.query_params.get('type')
        if room_type:
            queryset = queryset.filter(type=room_type)

        return queryset

    def get_serializer_class(self):
        return RoomSerializer

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        # queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class RoomDetailView(APIView):
    def get(self, request, pk, *args, **kwargs):
        try:
            room = Room.objects.get(id=pk)
            data = RoomSerializer(room).data

            return Response(data, status=status.HTTP_200_OK)
        
        except Exception:
            data = {
                "error": "topilmadi"
            }
            return Response(data, status=status.HTTP_404_NOT_FOUND)


class BookingRoomView(CreateAPIView):
    queryset = Booking.objects.all()
    
    def get_serializer_class(self):
        return BookingSerializer

    def post(self, request, pk, *args, **kwargs):
        room = get_object_or_404(Room.objects.all(), id=pk)
        print(request.data)

        try:
            resident_name = request.data.get('resident.name') # for html form data
        except Exception:
            resident_name = request.data['resident']['name'] # for json form data

        if resident_name is not None and resident_name.rstrip():
            resident, _ = Resident.objects.get_or_create(name=resident_name)
        else:
            return Response({
                "message": "Resident name cannot be blank"
            })
        start = request.data['start']
        end = request.data['end']

        try:
            # for handling raw data's start and end datetimes
            datetime_format = '%d-%m-%Y %H:%M:%S'    
            start = datetime.strptime(start, datetime_format)
            end = datetime.strptime(end, datetime_format)
        except Exception:
            pass  #do nothing for html form datetime

        data = {
            "resident": resident.id,
            'room': room.id,
            "start": start,
            "end": end
        }
        serialized_data = BookingSerializer(data=request.data, context={"room_id": room.id})
        

        if serialized_data.is_valid(raise_exception=True):
            
            # booking = Booking(resident=resident, room=room, start=start, end=end)
            bookingg = BookingRoomSerializer(data=data, context={"room_id": room.id})

            if bookingg.is_valid(raise_exception=True):
                bookingg.save()
                context = {
                    "message": "xona muvaffaqiyatli band qilindi"
                }    
                return Response(context)
            else:
                context = {
                    "error": "uzr, siz tanlagan vaqtda xona band"
                }
                return Response(context)
        else:
            context = {
                "malumotlar formati mos kelmadi"
            }
            return Response(context)
        

class RoomAvailabiltyAPIView(ListAPIView):
    filter_backends = [SearchFilter,]
    search_fields = ['start__date']


    def get_date(self, *args, **kwargs):
        date_ = self.request.query_params.get("search")
        if date_:
            date = datetime.strptime(date_, "%Y-%m-%d").date()
        else:
            date = timezone.localdate()
            print("bingo=",date)
            print(f"{timezone.localdate()=}")
        return date

    def get_queryset(self):
        queryset = Booking.objects.filter(room=self.kwargs.get("pk"))        
        date = self.get_date()
        queryset = queryset.filter(start__date=date)

        return queryset

    def generate_available_times(self, opening_time, closing_time, bookings, *args, **kwargs):
        time_zone = ZoneInfo(settings.TIME_ZONE)
        data = []
        first_booking_start = bookings[0].start

        if opening_time < first_booking_start:
            start = opening_time
            end = first_booking_start
            data.append({"start": start.astimezone(time_zone), "end": end.astimezone(time_zone)})
            print({"start": start.astimezone(time_zone), "end": end.astimezone(time_zone)})
        
        for i in range(len(bookings) - 1):
            current_end = bookings[i].end
            next_start = bookings[i+1].start
            if current_end < next_start:
                start = current_end
                end = next_start
                data.append({"start": start.astimezone(time_zone), "end": end.astimezone(time_zone)})
        
        last_booking_end = bookings[len(bookings) - 1].end
        if last_booking_end < closing_time:
            start = last_booking_end
            end = closing_time
            data.append({"start": start.astimezone(time_zone), "end": end.astimezone(time_zone)})
    
        return data

    def get(self, request, pk, *args, **kwargs):
        room = Room.objects.get(id=pk)
        date = self.get_date()
        
        opening_time = timezone.make_aware(datetime.combine(date, room.opening_time))
        closing_time = timezone.make_aware(datetime.combine(date, room.closing_time))

        bookings = self.get_queryset()
        if bookings:
            bookings = bookings.order_by('start__time')
            data = self.generate_available_times(opening_time=opening_time, closing_time=closing_time, bookings=bookings)
            
        else:
            data = {
                "start": opening_time,
                "end": closing_time
            }

        if data:
            return Response(data)
        else:
            return Response(
                {
                    "message": f"{date} sanasi uchun {room.name} xonasida bo'sh vaqtlar mavjud emas! :("
                }
            )
