from django.db import models


class Resident(models.Model):
    name = models.CharField(max_length=150)
    
    def __str__(self) -> str:
        return self.name


class Room(models.Model):
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=150)
    capacity = models.PositiveIntegerField()

    def __str__(self) -> str:
        return self.name


class Booking(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.DO_NOTHING)
    room = models.ForeignKey(Room, on_delete=models.DO_NOTHING, related_name="bookings")
    start = models.DateTimeField()
    end = models.DateTimeField()

    def __str__(self) -> str:
        return f"{self.room} booked by {self.resident}"


class AvailableRooms(models.Model):
    room = models.ForeignKey(Room, on_delete=models.DO_NOTHING, related_name="availablity")
    start = models.DateTimeField()
    end = models.DateTimeField()
    is_available = models.BooleanField(default=True)


