from django.contrib import admin
from .models import *

    
class MedicineStockInline(admin.TabularInline):
    model = MedicineStock
    fields = ['medicine', 'batchNo', 'noOfTabletsInStore', 'lastUpdated']  # batchNo should be here
    readonly_fields = ['medicine', 'noOfTabletsInStore', 'lastUpdated']  # batchNo should NOT be read-only
    extra = 0  # Extra rows to show in the form
    search_fields = ['medicine__medicineName']  # You can search by medicine name

class MedicineProcureDetailsInline(admin.TabularInline):
    model = MedicineProcureDetails
    fields = ['medicine', 'batchNo','pack', 'quantity', 'pricePerStrip', 'mrp', 'noOfTablets', 'pricePerTablet', 'dateOfPurchase', 'expiryDate']
    readonly_fields = ['noOfTablets', 'pricePerTablet']  # Make these read-only since they are calculated
    extra = 0  # Adds an empty row for adding new procurement details


# Now in your MedicineAdmin
class MedicineAdmin(admin.ModelAdmin):
    list_display = ['medicineName', 'medCategory']
    search_fields = ['medicineName']
    inlines = [MedicineProcureDetailsInline,MedicineStockInline]  # Add inlines here

admin.site.register(Category)  # Register Category model
admin.site.register(Medicine, MedicineAdmin) 
#admin.site.register(MedicineStock, MedicineStockAdmin)


admin.site.register(PatientDetail)
admin.site.register(Bill)
admin.site.register(Sale)

