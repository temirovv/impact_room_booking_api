from datetime import time

from django.db import models
from django.core.exceptions import ValidationError


class Resident(models.Model):
    name = models.CharField(max_length=150)  

    def __str__(self) -> str:
        return self.name


class Room(models.Model):
    ROOM_TYPES = [
        ('focus', 'Focus'),
        ('team', 'Team'),
        ('conference', 'Conference')
    ]

    name = models.CharField(max_length=200)
    type = models.CharField(max_length=11, choices=ROOM_TYPES)
    capacity = models.PositiveIntegerField()
    
    opening_time = models.TimeField(default=time(hour=0, minute=0, second=0))
    closing_time = models.TimeField(default=time(hour=23, minute=59, second=59))
    
    def __str__(self) -> str:
        return self.name

    def clean(self):
        rooms = Room.objects.filter(
            name__icontains = self.name,
            type = self.type,
        )

        if rooms.exists():
            raise ValidationError("This room already created!")


class Booking(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="bookings")
    start = models.DateTimeField()
    end = models.DateTimeField()

    def clean(self):
        if self.start is not None and self.end is not None and self.end <= self.start:
            raise ValidationError('End date cannot be less than or equals to start date!')
        
        if self.start.time() < self.room.opening_time or self.end.time() > self.room.closing_time:
            raise ValidationError(f"you can book this only from {self.room.opening_time} to {self.room.closing_time} ")
        
        if Booking.objects.filter(room = self.room,end__gt = self.start, start__lt = self.end).exists():
            raise ValidationError('this room already booked')

    def __str__(self) -> str:
        return f"{self.room} booked by {self.resident} from {self.start} to {self.end}"

