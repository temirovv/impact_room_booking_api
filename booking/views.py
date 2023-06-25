from datetime import datetime
from zoneinfo import ZoneInfo

from django.utils import timezone
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination

from .models import Room, Resident, Booking
from .serializers import RoomSerializer, BookingRoomSerializer


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
                'results': data
            }
        )


class RoomListAPIView(ListAPIView):
    queryset = Room.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['type']
    search_fields = ['name']
    pagination_class = CustomPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        search_name = self.request.query_params.get("search")
        type = self.request.query_params.get('type')

        if search_name and type:
            queryset = queryset.filter(
                name__icontains=search_name, 
                type=type
            )
        elif search_name:
            queryset = queryset.filter(name__icontains=search_name)
        elif type:
            queryset = queryset.filter(type=type)

        return queryset

    def get_serializer_class(self):
        return RoomSerializer

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


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


class BookingRoomView(APIView):
    queryset = Booking.objects.all()

    def get_serializer_class(self):
        return BookingRoomSerializer

    def post(self, request, *args, **kwargs):
        room = Room.objects.get(id=self.kwargs.get('pk'))
        try:
            resident_name = request.data['resident']['name']
        except Exception:
            raise Exception("error occured")

        if resident_name is not None and resident_name.rstrip():
            resident, _ = Resident.objects.get_or_create(name=resident_name)
        else:
            return Response({
                "error": "Resident nomi bo‘sh bo‘lishi mumkin emas"
            },
                status=status.HTTP_400_BAD_REQUEST
            )

        start = request.data['start']
        end = request.data['end']

        try:
            # kelgan sana va vaqtni kerakli formatga o‘tkazish
            datetime_format = settings.DATETIME_FORMAT
            start = datetime.strptime(start, datetime_format)
            end = datetime.strptime(end, datetime_format)
        except Exception:
            return Response(
                {
                    "error": f"siz sana va vaqtni ushbu ko'rinishda kiritishingiz kerak {datetime_format}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # serializer uchun data ni formatlash
        data = {
            "resident": resident.id,
            'room': room.id,
            "start": start,
            "end": end
        }
        serialized_data = BookingRoomSerializer(
            data=data, context={"room_id": room.id}
        )
        if serialized_data.is_valid():
            serialized_data.save()
            context = {
                "message": "xona muvaffaqiyatli band qilindi"
            }
            return Response(context, status=status.HTTP_201_CREATED)
        else:
            try:
                errors = serialized_data.errors['non_field_errors'][0]
                error_code = errors.code  # xatolik kodini olish
                error_message = str(errors)  # xatolik xabarini olish

                context = {
                    error_code: error_message,
                }
                return Response(context, status=status.HTTP_410_GONE)

            except Exception:
                return Response(serialized_data.errors, status=status.HTTP_410_GONE)


class RoomAvailabiltyAPIView(APIView):
    filter_backends = [SearchFilter,]
    search_fields = ['start__date']
    
    def get_date(self, *args, **kwargs):
        '''
            get_date -> metodi Xonaning bo'sh vaqtlarni ko'rish uchun api 
            orqali yuborilgan argumentni olish, tekshirish xususiyatiga ega.
            parametrlar -> self, *args, **kwargs

            maqsadi -> foydalanuvchi api orqali sanani kiritsa uni datetime
            modulidan foydalanib date formatiga o'zgartirish va o‘tgan sana 
            kiritilishini oldini olish. Agar foydalanuvchi sanani kiritmagan 
            bo'lsa bugungi(ayni vaqtdagi) sanani jo'natish.
        '''
        date_ = self.request.query_params.get("search")
        if date_:
            date = datetime.strptime(date_, "%Y-%m-%d").date()
        else:
            date = timezone.localdate()
        return date

    def get_current_time(self):
        current_time = timezone.localtime().__format__(settings.DATETIME_FORMAT)
        current_time = datetime.strptime(current_time, settings.DATETIME_FORMAT).time()

        return current_time
    
    def get_queryset(self):
        queryset = Booking.objects.filter(room=self.kwargs.get("pk"))
        date = self.get_date()
        # querysetdan berilgan sana bo'yicha bookinglarni filterlash
        queryset = queryset.filter(start__date=date) 
        return queryset

    def get_room(self):
        '''
            get_room -> metodi foydalanuvchi bo‘sh vaqlarini ko‘rishni 
            istayotgan xona obeyktini qaytaradi.

            maqsadi -> rooms/<int:pk>/availability dan pk ga mos keluvchi
            xona obyektini qaytarish.
        '''
        return Room.objects.get(id=self.kwargs.get('pk'))

    def generate_available_times(self, opening_time, closing_time, bookings, *args, **kwargs):
        '''
            generate_available_times -> metodi xonaning bo'sh vaqtlarini 
            aniqlaydi va qaytaradi.

            maqsadi -> mavjud xonaning ma'lum bir sanadagi band qilingan 
            vaqtlaridan foydalanib uning bo'sh vaqtlarini hisoblash

            parametrlar -> self, opening_time, closing_time, bookings, ...
            bu yerda:
                opening_time: xonaning ochilish vaqti,
                closing_time: xonaning yopilish vaqti,
                bookings: band qilingan xonalar ro‘yhati(queryset)
        '''
        time_zone = ZoneInfo(settings.TIME_ZONE)
        data = []
        first_booking_start = bookings[0].start

        # agar birinchi band qilingan vaqtdan oldin bo'sh vaqt bo'lsa
        if opening_time < first_booking_start:
            start = opening_time
            end = first_booking_start
            data.append({"start": start.astimezone(time_zone),
                        "end": end.astimezone(time_zone)})

        # birinchi bookingdan keyingi bo'sh vaqtlar
        for i in range(len(bookings) - 1):
            current_end = bookings[i].end
            next_start = bookings[i+1].start
            if current_end < next_start:
                start = current_end
                end = next_start
                data.append({"start": start.astimezone(time_zone),
                            "end": end.astimezone(time_zone)})

        # agar oxirgi bookingdan keyin bo'sh vaqt bo'lsa
        last_booking_end = bookings[len(bookings) - 1].end
        if last_booking_end < closing_time:
            start = last_booking_end
            end = closing_time
            data.append({"start": start.astimezone(time_zone),
                        "end": end.astimezone(time_zone)})

        return data

    def make_aware(self, date_, time_, *args, **kwargs):
        '''
            make_aware -> metodi berilgan sana va vaqtni
            timezone infoni o'z ichiga olgan datetime ga
            convert qiladi.
            parametrlar -> date_ , time_

            maqsadi -> dasturda vaqtlarni taqqoslashdagi 
            muammolarni oldini olish
        '''
        return timezone.make_aware(datetime.combine(date_, time_))

    def check_time_for_today(self):
        current_time = self.get_current_time()
        room = self.get_room()
        date = self.get_date()
        times = {}
        if date == timezone.localdate():
            if room.opening_time < current_time and room.closing_time > current_time:
                times['opening_time'] = self.make_aware(date, current_time)
                times['closing_time'] = self.make_aware(date, room.closing_time)
                return times
            else:
                return None
        else:
            return None
        
    def get(self, request, pk, *args, **kwargs):
        room = self.get_room() # ayni vaqtdagi xonani olish
        date = self.get_date() # sanani olish

        times = self.check_time_for_today()
        if times:
            opening_time = times['opening_time']
            closing_time = times['closing_time']
        else:
            opening_time = self.make_aware(date, room.opening_time) # sana va vaqtni         
            closing_time = self.make_aware(date, room.closing_time) # birlashtirish

        # band qilingan xonalarni olish
        bookings = self.get_queryset()
        if bookings:
            bookings = bookings.order_by('start__time') #ularni vaqt bo'yicha tartiblash
            data = self.generate_available_times(
                opening_time=opening_time,
                closing_time=closing_time,
                bookings=bookings
            )
        else: 
            # agar berilgan sanada hech qanday bookinglar bo'lmasa
            # uning bo'sh vaqtlarni xonaning ochilish va yopilish
            # vaqtiga teng bo'ladi
            data = [{
                "start": opening_time,
                "end": closing_time
            }]
        
        if data:
            return Response(
                data,
                status=status.HTTP_200_OK
            )
        else:
            # agar xonalar kun davomida band bo'lsa
            return Response(
                {
                    "message": f"{date} sanasi uchun {room.name} xonasida bo'sh vaqtlar mavjud emas! :("
                },
                status=status.HTTP_404_NOT_FOUND
            )
