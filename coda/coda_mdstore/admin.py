from coda_mdstore.models import Bag, Bag_Info, Node, External_Identifier
from django.contrib import admin


class Bag_InfoInline(admin.TabularInline):
    model = Bag_Info


class BagInfoAdmin(admin.ModelAdmin):
    list_display = ('bag_name', 'field_name')


class BagAdmin(admin.ModelAdmin):
    inlines = [Bag_InfoInline]
    list_display = ('name', 'size', 'files', 'last_verified_date')
    list_filter = ['last_verified_date']
    search_fields = ['name']


class NodeAdmin(admin.ModelAdmin):
    list_display = ("node_url", "node_path", "node_capacity", "node_size")


class External_IdentifierAdmin(admin.ModelAdmin):
    list_display = ("value", "belong_to_bag")


admin.site.register(Bag, BagAdmin)
admin.site.register(Bag_Info, BagInfoAdmin)
admin.site.register(Node, NodeAdmin)
admin.site.register(External_Identifier, External_IdentifierAdmin)
