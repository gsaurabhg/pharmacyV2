from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import *
from django.db import transaction


# Purpose: This table holds medicine categories (e.g., Ob-Gyn, Urology, General Medicine, etc.).
# Field name: The name of the category (e.g., "Ob-Gyn", "Urology").
# Usage: Each medicine will be assigned to one of these categories.
class Category(models.Model):
    name = models.CharField("Category Name", max_length=100, unique=True)

    def __str__(self):
        return self.name


# Purpose: Stores medicine details including a foreign key reference to Category.
# Field medicineName: The name of the medicine.
# Field medCategory: A foreign key linking to the Category table to classify the medicine.
class Medicine(models.Model):
    medicineName = models.CharField("Product Name", max_length=48, blank=False)
    medCategory = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.medicineName

# Purpose: Tracks the procurement event for each medicine including quantity, cost, MRP, and procurement date.
# Fields noOfTablets and pricePerTablet: These are calculated fields based on the quantity purchased and the pack size.
# Reason for batchNo: This field is indirectly represented in the MedicineStock table, but can be implicitly managed per procurement event. 
class MedicineProcureDetails(models.Model):
    pharmacy_user = models.ForeignKey('auth.User',on_delete=models.CASCADE)
    medicine = models.ForeignKey('Medicine', on_delete=models.CASCADE)
    batchNo = models.CharField("Batch Number", max_length=50, blank=False, default="1")  # Track batch number directly, its redundant and is stored in stock table too. Opt opp.
    pack = models.PositiveSmallIntegerField("No. of tablets per strip/bottle",default =1)
    quantity = models.PositiveSmallIntegerField("Number of strips/pieces purchased")
    pricePerStrip = models.DecimalField("Price per strip/piece",max_digits=8, decimal_places=2,validators=[MinValueValidator(Decimal('0.01'))])
    mrp = models.DecimalField("M.R.P. per Strip", max_digits=8, decimal_places=2)
    dateOfPurchase = models.DateField("Date Of Purchase",default=timezone.now)
    expiryDate = models.DateField("Expiry Date")
    # These fields are calculated dynamically:
    noOfTablets = models.PositiveSmallIntegerField(default =0)
    pricePerTablet = models.DecimalField(max_digits=8, decimal_places=2,default ='0.01',validators=[MinValueValidator(Decimal('0.01'))])

    @transaction.atomic
    def save(self, *args, **kwargs):
        self.noOfTablets = self.quantity * self.pack
        self.pricePerTablet = round(self.mrp / self.pack, 2)

        # Check if stock already exists with same batch and medicine
        existing_stock = MedicineStock.objects.filter(
            medicine=self.medicine,
            batchNo=self.batchNo
        ).first()

        if existing_stock:
            existing_price = existing_stock.procurement.pricePerTablet
            if round(existing_price, 2) != self.pricePerTablet:
                raise ValidationError(
                    f"Inconsistent pricing for batch {self.batchNo} of {self.medicine}. "
                    f"Existing price/tablet is {existing_price}, new is {self.pricePerTablet}."
                )

        super().save(*args, **kwargs)
        self.update_stock(self.batchNo)

    def update_stock(self, batch_no):
        # Check if the stock record already exists for this medicine and batch number
        try:
            # Fetch the stock for the given medicine and batch number
            stock = MedicineStock.objects.get(medicine=self.medicine, batchNo=batch_no)
            # Update the number of tablets in store (increment by the number of tablets from this procurement)
            stock.noOfTabletsInStore += self.noOfTablets
            stock.save()
        except MedicineStock.DoesNotExist:
            # If no stock record exists, create a new one
            MedicineStock.objects.create(
                medicine=self.medicine,
                batchNo=batch_no,
                procurement=self,  # Link procurement to stock
                noOfTabletsInStore=self.noOfTablets
            )

 
    def __str__(self):
        return f"Procurement of {self.medicine.medicineName} - Date: {self.dateOfPurchase} - Quantity: {self.quantity} "

# Purpose: Tracks the stock of medicines, including batch number and total tablets in store. Each stock record is linked to a procurement event.
# Fields noOfTabletsInStore: Represents the total number of tablets available in stock for the given batch of medicine.
# unique_together = ('medicine', 'batchNo') ensures that the same medicine and batch combination is not repeated.
class MedicineStock(models.Model):
    medicine = models.ForeignKey('Medicine', on_delete=models.CASCADE)  # ForeignKey to Medicine model
    batchNo = models.CharField("Batch Number", max_length=50)  # Track batch number directly
    procurement = models.ForeignKey('MedicineProcureDetails', on_delete=models.CASCADE)  # Link to procurement event
    noOfTabletsInStore = models.PositiveSmallIntegerField("Total Tablets in Store", default=0)
    lastUpdated = models.DateTimeField(auto_now=True)  # Timestamp of the last stock update

    class Meta:
        unique_together = ('medicine', 'batchNo')  # Ensure that each medicine-batch combo is unique

    def save(self, *args, **kwargs):
        if self.noOfTabletsInStore < 0:
            raise ValueError("Tablets in store cannot be negative.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.medicine.medicineName} - Batch: {self.batchNo}"


########################################
# case 1: Same medicine and same batch number but multiple procurements
# EXAMPLE:
#### First procurement: Batch "A123", quantity=10 strips, pack=10, noOfTablets = 10 * 10 = 100 tablets.
#### Second procurement (same batch "A123"): quantity=5 strips, pack=10, noOfTablets = 5 * 10 = 50 tablets.
# Results:
#### MedicineProcureDetails: Two records will be created for batch "A123" with different procurement dates.
#### MedicineStock: noOfTabletsInStore for batch "A123" will be 100 + 50 = 150 tablets.

# case 2: Same medicine but different batch number for multiple procurements
# EXAMPLE:
#### First procurement: Batch "A123", quantity=10 strips, pack=10, noOfTablets = 100 tablets.
#### Second procurement  (new batch "B456"): quantity=5 strips, pack=10, noOfTablets = 50 tablets.
# Results:
#### MedicineProcureDetails: Two records will be created, one for batch "A123" and another for batch "B456".
#### MedicineStock: The noOfTabletsInStore for batch "A123" will remain 100 tablets, and for batch "B456", it will be 50 tablets.
########################################

# Purpose: Records each sale transaction, updates the stock, and calculates the sale amount based on the number of tablets sold.
# How it works:
#### For each sale, the stock for the specific medicine-batch combination is updated.
#### The sale amount is computed as noOfTabletsSold * pricePerTablet.
class Sale(models.Model):
    medicine = models.ForeignKey('Medicine', on_delete=models.CASCADE)
    stock = models.ForeignKey('MedicineStock', on_delete=models.CASCADE)  # Reference to medicine Stock
    noOfTabletsSold = models.PositiveIntegerField("Quantity Sold")
    sale_amount = models.DecimalField("Sale Amount", max_digits=8, decimal_places=2)
    sale_date = models.DateTimeField("Sale Date", default=timezone.now)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.stock.noOfTabletsInStore >= self.noOfTabletsSold:
                self.stock.noOfTabletsInStore -= self.noOfTabletsSold
                self.stock.save()
                self.sale_amount = Decimal(self.noOfTabletsSold) * self.stock.procurement.pricePerTablet
                self.sale_amount = self.sale_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                super().save(*args, **kwargs)
            else:
                raise ValueError("Not enough stock to fulfill the sale. Please select a different Batch No")

    def __str__(self):
        return f"Sale of {self.medicine.medicineName} - {self.noOfTabletsSold} tablets"

class PatientDetail(models.Model):
    patientID = models.CharField("Patient ID",max_length=50, blank=True)
    patientName = models.CharField("Name",max_length=50, blank=True)
    patientPhoneNo = models.PositiveSmallIntegerField("Phone Number", blank=True, default = '0')

    def publish(self):
        self.save()

    def __str__(self):
        return self.patientID

DISCOUNT_CHOICES = ((0, 0), (5, 5), (10, 10))

class Bill(models.Model):
    patientID = models.ForeignKey(PatientDetail, on_delete=models.CASCADE)
    medStock = models.ForeignKey(MedicineStock, on_delete=models.CASCADE)
    
    billNo = models.CharField(max_length=50)
    billDate = models.DateField("Date Of Purchase", default=timezone.now)

    noOfTabletsOrdered = models.PositiveSmallIntegerField(default=0)
    totalPrice = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, validators=[MinValueValidator(Decimal('0.01'))])
    discount = models.PositiveSmallIntegerField("Discount (%)", choices=DISCOUNT_CHOICES, default=0)
    discountedPrice = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, validators=[MinValueValidator(Decimal('0.01'))])

    transactionCompleted = models.CharField(max_length=1, default='N')  # Could be 'Y' or 'N'
    
    # Return-related fields
    returnSales = models.CharField(max_length=2, default='N')  # Could be 'Y'/'N'
    returnSalesNoOfTablets = models.PositiveSmallIntegerField(default=0)
    returnSalesBillDate = models.DateField("Date Of Return", default=timezone.now)
    returnDiscountedPrice = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, validators=[MinValueValidator(Decimal('0.01'))])

    def __str__(self):
        return f"Bill #{self.billNo} - {self.patientID.patientName}"

    def calculate_totals(self):
        """ Optional: helper method to compute totals """
        self.totalPrice = self.noOfTabletsOrdered * self.medStock.procurement.pricePerTablet
        self.discountedPrice = self.totalPrice * Decimal(1 - self.discount / 100)
        self.totalPrice = self.totalPrice.quantize(Decimal('0.01'))
        self.discountedPrice = self.discountedPrice.quantize(Decimal('0.01'))

    def save(self, *args, **kwargs):
        self.calculate_totals()
        super().save(*args, **kwargs)


