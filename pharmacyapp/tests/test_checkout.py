from django.test import TestCase, Client
from django.urls import reverse
from pharmacyapp.models import (
    PatientDetail, Medicine, Category,
    MedicineProcureDetails, MedicineStock,
    Bill, Sale
)
from django.utils import timezone
from decimal import Decimal
import datetime
from django.contrib.auth.models import User

class CheckoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testadmin',
            password='password123',
            is_staff=True,        # For admin interface or @staff_member_required
            is_superuser=True     # For full access
        )
        self.client = Client()
        self.client.login(username='testadmin', password='password123')
        self.patient = PatientDetail.objects.create(
            patientName='Alice',
            patientPhoneNo='5554443333',
            patientID='AMC-CHECK'
        )
        cat = Category.objects.create(name='General')
        med = Medicine.objects.create(medicineName='Ibuprofen', medCategory=cat)
        procure = MedicineProcureDetails.objects.create(
            pharmacy_user = self.user,
            medicine = med,
            batchNo = 'B100',
            pack = 10,
            quantity = 2,
            pricePerStrip = Decimal('100'),
            mrp = Decimal('100'),
            expiryDate = timezone.now().date() + datetime.timedelta(days=60)
        )
        self.stock = MedicineStock.objects.get(medicine=med, batchNo='B100')
        # Add to cart via Bill
        self.bill = Bill.objects.create(
            patientID = self.patient,
            medStock = self.stock,
            noOfTabletsOrdered = 5,
            totalPrice = Decimal('50'),
            discount = 0,
            discountedPrice = Decimal('50'),
            billNo = 'SSDS-TEST',
            billDate = timezone.now(),
            transactionCompleted = 'N'
        )

    def test_checkout_redirection_and_sale(self):
        url = reverse('medicine_checkout', args=[self.patient.pk])
        response = self.client.post(url)
        # Expect redirect after successful checkout
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('final_bill_view', args=[self.bill.billNo])))
        # Verify side effects
        self.bill.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(self.bill.transactionCompleted, 'Y')
        # From 20 tablets originally, 5 sold => 15 remain
        self.assertEqual(self.stock.noOfTabletsInStore, 15)
        sale = Sale.objects.get(stock=self.stock)
        self.assertEqual(sale.noOfTabletsSold, 5)
        self.assertEqual(sale.sale_amount, Decimal('5') * self.stock.procurement.pricePerTablet)
