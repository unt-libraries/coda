from coda_validate.models import Validate
from django.contrib import admin


class ValidateAdmin(admin.ModelAdmin):
    date_hierarchy = 'last_verified'
    fields = ('last_verified',)


admin.site.register(Validate, ValidateAdmin)
