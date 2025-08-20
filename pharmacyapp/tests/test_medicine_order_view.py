from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from pharmacyapp.models import (
    PatientDetail,
    Category,
    Medicine,
    MedicineProcureDetails,
    MedicineStock,
    Bill,
)
from django.contrib.auth.models import User
import datetime


class MedicineOrderViewTests(TestCase):
    def setUp(self):
        # Create a test user and login
        self.user = User.objects.create_user(
            username='testadmin',
            password='password123',
            is_staff=True,
            is_superuser=True,
        )
        self.client = Client()
        self.client.login(username='testadmin', password='password123')

        # Create patient
        self.patient = PatientDetail.objects.create(
            patientID="P1234",
            patientName="John Doe",
            patientPhoneNo=9991234567
        )

        # Create Category
        self.category = Category.objects.create(name="General Medicine")

        # Create Medicine
        self.medicine = Medicine.objects.create(
            medicineName="Paracetamol",
            medCategory=self.category
        )

        # Create first procurement for batch "BATCH001"
        self.procurement1 = MedicineProcureDetails.objects.create(
            pharmacy_user=self.user,
            medicine=self.medicine,
            batchNo="BATCH001",
            pack=10,
            quantity=5,  # 5 strips * 10 = 50 tablets
            pricePerStrip=Decimal('50.00'),
            mrp=Decimal('50.00'),
            expiryDate=timezone.now().date() + datetime.timedelta(days=365)
        )

        # Create second procurement for SAME batch "BATCH001" (to test cumulative stock)
        self.procurement2 = MedicineProcureDetails.objects.create(
            pharmacy_user=self.user,
            medicine=self.medicine,
            batchNo="BATCH001",
            pack=10,
            quantity=3,  # 3 strips * 10 = 30 tablets
            pricePerStrip=Decimal('50.00'),
            mrp=Decimal('50.00'),
            expiryDate=timezone.now().date() + datetime.timedelta(days=365)
        )

        # Fetch MedicineStock for batch "BATCH001"
        self.stock = MedicineStock.objects.get(medicine=self.medicine, batchNo="BATCH001")

    def test_procurement_cumulative_stock(self):
        # Total tablets = 50 + 30 = 80
        self.assertEqual(self.stock.noOfTabletsInStore, 80)

    def test_add_medicine_to_cart_uses_existing_patient_instance(self):
        """
        Simulate posting a medicine order for existing patient and check if Bill is created correctly.
        This assumes your view 'medicine_order' expects patient pk and form data including batchNo, orderQuantity, discount.
        """

        url = reverse('medicine_order', kwargs={'pk': self.patient.pk})

        post_data = {
            'medicineName': self.medicine.medicineName,
            'batchNo': self.stock.batchNo,
            'orderQuantity': '5',  # ordering 5 tablets
            'discount': '10',      # 10% discount
            'addMed': 'true',
        }

        response = self.client.post(url, data=post_data, follow=True)

        # Assert response OK (200) or redirect after post
        self.assertIn(response.status_code, [200, 302])

        # Check Bill created
        bill = Bill.objects.first()
        self.assertIsNotNone(bill)

        # Check Bill fields
        self.assertEqual(bill.patientID, self.patient)
        self.assertEqual(bill.medStock, self.stock)
        self.assertEqual(bill.noOfTabletsOrdered, 5)

        # Calculate expected price: 5 tablets * pricePerTablet (mrp/pack = 50/10 = 5.00 per tablet)
        expected_price_per_tablet = self.procurement1.pricePerStrip / self.procurement1.pack  # 50 / 10 = 5.0
        expected_total_price = Decimal('5') * expected_price_per_tablet  # 5 tablets * 5.0 = 25.00

        self.assertEqual(bill.totalPrice, expected_total_price.quantize(Decimal('0.01')))
        self.assertEqual(bill.discount, 10)
        self.assertEqual(bill.transactionCompleted, 'N')

        # Optional: check response contains success message (customize as per your actual template/view)
        self.assertContains(response, "Added medicine in Cart")
