#from coda_mdstore.models import Bag, Bag_Info, Node#, QueueEntry
from coda_replication.models import QueueEntry
from django.contrib import admin


class QueueAdmin(admin.ModelAdmin):
    list_display = ("ark", "oxum", "status")
    search_fields = ["ark"]
    list_filter = ["status"]

admin.site.register(QueueEntry, QueueAdmin)
