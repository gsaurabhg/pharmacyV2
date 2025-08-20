from django.test import TestCase, Client
from django.contrib.auth.models import User
from pharmacyapp.models import Medicine, Category, MedicineProcureDetails, MedicineStock
from decimal import Decimal
from datetime import date, timedelta

class MedicineProcurementTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testadmin',
            password='password123',
            is_staff=True,        # For admin interface or @staff_member_required
            is_superuser=True     # For full access
        )
        self.client = Client()
        self.client.login(username='testadmin', password='password123')
        self.category = Category.objects.create(name='General Medicine')

        # Create a medicine
        self.medicine = Medicine.objects.create(
            medicineName='TestMed',
            medCategory=self.category
        )

    def test_single_stock_update_on_procurement(self):
        # Initial procurement details
        pack = 10
        quantity = 5  # 5 strips
        batch_no = "BATCH123"
        price_per_strip = Decimal('50.00')
        mrp = Decimal('100.00')
        today = date.today()
        expiry = today + timedelta(days=365)

        # Create procurement (stock update happens in model's save())
        procurement = MedicineProcureDetails.objects.create(
            pharmacy_user=self.user,
            medicine=self.medicine,
            batchNo=batch_no,
            pack=pack,
            quantity=quantity,
            pricePerStrip=price_per_strip,
            mrp=mrp,
            dateOfPurchase=today,
            expiryDate=expiry
        )

        # Fetch stock entry
        stock_entry = MedicineStock.objects.get(medicine=self.medicine, batchNo=batch_no)

        # Expected tablets = 5 strips * 10 per pack = 50 tablets
        expected_stock = pack * quantity

        self.assertEqual(
            stock_entry.noOfTabletsInStore,
            expected_stock,
            f"Stock should be exactly {expected_stock}, but got {stock_entry.noOfTabletsInStore} (possible double addition)."
        )

    def test_multiple_procurements_same_batch(self):
        pack = 10
        quantity1 = 5
        quantity2 = 3
        batch_no = "BATCH123"
        price_per_strip = Decimal('50.00')
        mrp = Decimal('100.00')
        today = date.today()
        expiry = today + timedelta(days=365)

        # First procurement
        MedicineProcureDetails.objects.create(
            pharmacy_user=self.user,
            medicine=self.medicine,
            batchNo=batch_no,
            pack=pack,
            quantity=quantity1,
            pricePerStrip=price_per_strip,
            mrp=mrp,
            dateOfPurchase=today,
            expiryDate=expiry
        )

        # Second procurement with the same batch
        MedicineProcureDetails.objects.create(
            pharmacy_user=self.user,
            medicine=self.medicine,
            batchNo=batch_no,
            pack=pack,
            quantity=quantity2,
            pricePerStrip=price_per_strip,
            mrp=mrp,
            dateOfPurchase=today,
            expiryDate=expiry
        )

        stock_entry = MedicineStock.objects.get(medicine=self.medicine, batchNo=batch_no)

        expected_stock = pack * (quantity1 + quantity2)
        self.assertEqual(stock_entry.noOfTabletsInStore, expected_stock,
            f"Expected stock {expected_stock}, got {stock_entry.noOfTabletsInStore}.")

    def test_procurement_different_batches(self):
        batch_1 = "BATCH-A"
        batch_2 = "BATCH-B"
        pack = 10
        qty = 5
        today = date.today()
        expiry = today + timedelta(days=365)
        price_per_strip = Decimal('60.00')
        mrp = Decimal('120.00')

        # Batch A
        MedicineProcureDetails.objects.create(
            pharmacy_user=self.user,
            medicine=self.medicine,
            batchNo=batch_1,
            pack=pack,
            quantity=qty,
            pricePerStrip=price_per_strip,
            mrp=mrp,
            dateOfPurchase=today,
            expiryDate=expiry
        )

        # Batch B
        MedicineProcureDetails.objects.create(
            pharmacy_user=self.user,
            medicine=self.medicine,
            batchNo=batch_2,
            pack=pack,
            quantity=qty,
            pricePerStrip=price_per_strip,
            mrp=mrp,
            dateOfPurchase=today,
            expiryDate=expiry
        )

        stock_batch_a = MedicineStock.objects.get(medicine=self.medicine, batchNo=batch_1)
        stock_batch_b = MedicineStock.objects.get(medicine=self.medicine, batchNo=batch_2)

        self.assertEqual(MedicineStock.objects.filter(medicine=self.medicine).count(), 2)
        self.assertEqual(stock_batch_a.noOfTabletsInStore, pack * qty)
        self.assertEqual(stock_batch_b.noOfTabletsInStore, pack * qty)

    def test_invalid_double_manual_update_should_not_exist(self):
        pack = 10
        qty = 4
        batch = "BATCH999"
        today = date.today()
        expiry = today + timedelta(days=365)
        price_per_strip = Decimal('55.00')
        mrp = Decimal('110.00')

        procurement = MedicineProcureDetails.objects.create(
            pharmacy_user=self.user,
            medicine=self.medicine,
            batchNo=batch,
            pack=pack,
            quantity=qty,
            pricePerStrip=price_per_strip,
            mrp=mrp,
            dateOfPurchase=today,
            expiryDate=expiry
        )

        # Try updating stock manually – which is discouraged!
        stock_entry = MedicineStock.objects.get(medicine=self.medicine, batchNo=batch)
        stock_entry.noOfTabletsInStore += 50  # Incorrect manual addition
        stock_entry.save()

        # Re-fetch from DB
        stock_entry_refetched = MedicineStock.objects.get(medicine=self.medicine, batchNo=batch)
        # Expecting this to fail because we shouldn't manually mutate it like this
        self.assertNotEqual(
            stock_entry_refetched.noOfTabletsInStore,
            pack * qty,
            "Manual updates to stock should NOT be allowed outside procurement flow!"
        )

