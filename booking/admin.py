from django.contrib import admin
from .models import Resident, Room, Booking


admin.site.register(Resident)
admin.site.register(Room)
admin.site.register(Booking)
