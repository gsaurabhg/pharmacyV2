from django.test import TestCase, Client
from django.urls import reverse
from pharmacyapp.models import Category, Medicine, MedicineProcureDetails, MedicineStock, PatientDetail, Bill
from django.utils import timezone
from decimal import Decimal
import datetime
from django.contrib.auth.models import User

class OrderingTests(TestCase):
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
            patientName='Jane',
            patientPhoneNo='123456789',
            patientID='AMC-TEST1234'
        )
        cat = Category.objects.create(name='General')
        med = Medicine.objects.create(medicineName='Paracetamol', medCategory=cat)
        procure = MedicineProcureDetails.objects.create(
            pharmacy_user = self.user,
            medicine = med,
            batchNo = 'B1',
            pack = 10,
            quantity = 10,
            pricePerStrip = Decimal('50'),
            mrp = Decimal('100'),
            expiryDate = timezone.now().date() + datetime.timedelta(days=30)
        )
        self.stock = MedicineStock.objects.get(medicine=med, batchNo='B1')

    def test_add_to_cart(self):
        url = reverse('medicine_order', args=[self.patient.pk])
        response = self.client.post(url, {
            'addMed': '1',
            'medicineName': 'Paracetamol',
            'batchNo': 'B1',
            'orderQuantity': '5',
            'discount': '10'
        })
        self.assertEqual(response.status_code, 200)
        bill = Bill.objects.first()
        self.assertEqual(bill.noOfTabletsOrdered, 5)
        self.assertEqual(bill.discount, 10)
        # confirm total and discounted price
        self.assertEqual(bill.totalPrice, Decimal('50'))  # 5 tablets * ?10 each
        expected_disc = Decimal('50') * Decimal('0.9')
        self.assertAlmostEqual(bill.discountedPrice, expected_disc)

