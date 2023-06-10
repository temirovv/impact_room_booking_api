from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Booking, Room, Resident
from django.utils import timezone


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ('id', 'name', 'type', 'capacity')


class ResidentSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=150)

    class Meta:
        model = Resident
        fields = ('id', 'name', )


# kelgan ma'lumotni validatsiyadan o‘tkazish uchun
# va foydalanuvchiga xonani kiritmasdan to‘ldira 
# olishi uchun form data va raw datalarni jo‘natish maqsadida 
# yaratilgan serializer
class BookingSerializer(serializers.ModelSerializer):
    resident = ResidentSerializer()

    class Meta:
        model = Booking
        fields = ('resident', 'start', 'end')


    def validate(self, attrs, *args, **kwargs): 
        
        start = attrs['start']
        end = attrs['end']
        # agar 'start' uchun kiritilgan sana oldingi sana bo‘lsa
        if timezone.localdate() > start.date():
            raise ValidationError("O'tgan vaqt uchun bron qilolmaysiz")

        # if start is not None and end is not None and end <= start:
        # agar 'start' uchun kiritilgan sana va vaqt 'end' uchun kiritilgan vaqtdan oldin keyin kelsa
        if end <= start:
            raise ValidationError("boshlanish vaqti tugash vaqtidan keyin kelolmaydi! ")
        
        # residentlar xonani faqat eng ko‘pi bilan bir kun uchun band
        # qila olishini ta'minlash
        if start.date() != end.date():
            raise ValidationError("Siz xonani eng ko‘pi bilan bir kun uchun band qila olishingiz mumkin")
    
        return attrs


# foydalanuvchidan kelgan ma'lumotni saqlash uchun va 
# yana bir bor tekshirish uchun serializer
class BookingRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ('resident', 'room', 'start', 'end')
    
    def validate(self, data):
        room = data['room']
        start = data['start']
        end = data['end']
        
        # agar foydalanuvchi kiritgan vaqt xonaning ish vaqtiga nomutanosib bo‘lsa
        if start.time() < room.opening_time or end.time() > room.closing_time:
            raise ValidationError(f"you can book this only from {room.opening_time} to {room.closing_time} ")
        
        # end_gt=start -> Kiritilgan "end" sana va vaqti "start" sana va vaqtidan keyin(katta) bo‘lishi
        # start_lt=end -> Kiritilgan "start" sana va vaqti 'end" sana va vaqtidan oldin(kichik) bo‘lishi
        bookings = Booking.objects.filter(room = room, end__gt = start, start__lt = end)
        
        # agar shu vaqtda xonani bron qilishgan bo‘lsa 
        if bookings.exists():
            raise ValidationError('this room already booked')

        return data
