from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Booking, Room
from django.utils import timezone


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ('id', 'name', 'type', 'capacity')


class BookingRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ('resident', 'room', 'start', 'end')
    
    def validate(self, data):
        room = data['room']
        start = data['start']
        end = data['end']
        
        # agar 'start' uchun kiritilgan sana oldingi sana bo‘lsa
        if timezone.localdate() > start.date():
            raise ValidationError(
                "O'tgan vaqt uchun bron qilolmaysiz",
                code='error'
                )

        # agar 'start' uchun kiritilgan sana va vaqt 'end' uchun kiritilgan vaqtdan keyin kelsa
        if end <= start:
            raise ValidationError(
                "boshlanish vaqti tugash vaqtidan keyin kelolmaydi!",
                code='error'
                )
        
        # residentlar xonani faqat eng ko‘pi bilan bir kun uchun band
        # qila olishini ta'minlash
        if start.date() != end.date():
            raise ValidationError(
                "Siz xonani eng ko‘pi bilan bir kun uchun band qila olishingiz mumkin",
                code='error'
                )

        # agar foydalanuvchi kiritgan vaqt xonaning ish vaqtiga nomutanosib bo‘lsa
        if start.time() < room.opening_time or end.time() > room.closing_time:
            raise ValidationError(
                f"Siz ushbu xonani faqatgina soat {room.opening_time} dan {room.closing_time} gacha band qila olasiz ",
                code="error"
                )
        
        # end_gt=start -> Kiritilgan "end" sana va vaqti "start" sana va vaqtidan keyin(katta) bo‘lishi
        # start_lt=end -> Kiritilgan "start" sana va vaqti 'end" sana va vaqtidan oldin(kichik) bo‘lishi
        bookings = Booking.objects.filter(room = room, end__gt = start, start__lt = end)
        
        # agar shu vaqtda xonani bron qilishgan bo‘lsa 
        if bookings.exists():
            raise ValidationError('uzr, siz tanlagan vaqtda xona band', code="error")

        return data
