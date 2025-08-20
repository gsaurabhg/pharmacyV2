from django.test import TestCase, Client
from django.urls import reverse
from pharmacyapp.models import *
from pharmacyapp.forms import PatientForm
from uuid import uuid4
from django.contrib.auth.models import User
from uuid import uuid4
from decimal import Decimal
from django.utils import timezone
import datetime

class PatientTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testadmin',
            password='password123',
            is_staff=True,        # For admin interface or @staff_member_required
            is_superuser=True     # For full access
        )
        self.client = Client()
        self.client.login(username='testadmin', password='password123')
        self.data = {
            'patientName': 'John Doe',
            'patientPhoneNo': '1234567890',
        }

    def test_register_new_patient(self):
        patient_id = f"AMC-{uuid4().hex[:8]}"
        response = self.client.post(reverse('patient_details'), {
            'newReg': '1',
            'patientName': self.data['patientName'],
            'patientPhoneNo': self.data['patientPhoneNo'],
            'patientID': patient_id,
        }, follow=False)

        print(response.status_code)
        print(response.content.decode())  # see what the response HTML says (might include errors)

        self.assertEqual(response.status_code, 302)
    
    def test_search_patient_by_name(self):
        PatientDetail.objects.create(
            patientName='Alice Smith',
            patientPhoneNo='9998887777',
            patientID=f"AMC-{uuid4().hex[:8]}"
        )
        response = self.client.post(reverse('patient_details'), {
            'search': '1',
            'patientName': 'Alice',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alice Smith')

    def test_register_new_patient_and_follow_redirect(self):
        response = self.client.post(reverse('patient_details'), {
            'newReg': '1',
            'patientName': self.data['patientName'],
            'patientPhoneNo': self.data['patientPhoneNo'],
        }, follow=True)  # follow redirects

        # After following the redirect, status code should be 200 (final page loads)
        self.assertEqual(response.status_code, 200)

        # Verify that the patient was created in the database
        p = PatientDetail.objects.first()
        self.assertIsNotNone(p)
        self.assertTrue(p.patientID.startswith('AMC-'))

        # Optionally check that the final redirected page contains some expected content
        # For example, if it redirects to 'bill_details' page, check for patient name or bill header
        self.assertContains(response, self.data['patientName'])

#Test submitting search with no criteria
    def test_search_no_criteria_redirects(self):
        response = self.client.post(reverse('patient_details'), {
            'search': '1',
            'patientName': '',
            'patientID': '',
            'patientPhoneNo': '',
        }, follow=True)
        self.assertRedirects(response, reverse('patient_details'))
        messages = list(response.context['messages'])
        self.assertTrue(any("Enter one of the fields" in str(m) for m in messages))

#Test patient registration when phone number is missing
    def test_new_registration_without_phone_number_shows_message(self):
        response = self.client.post(reverse('patient_details'), {
            'newReg': '1',
            'patientName': 'NoPhoneUser',
            'patientPhoneNo': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter Phone Number")

#Test patient registration when patient already exists
    def test_new_registration_existing_patient_shows_message(self):
        # Create existing patient first
        PatientDetail.objects.create(
            patientName='Jane Doe',
            patientPhoneNo='5551234567',
            patientID=f"AMC-{uuid4().hex[:8]}"
        )
        response = self.client.post(reverse('patient_details'), {
            'newReg': '1',
            'patientName': 'Jane Doe',
            'patientPhoneNo': '5551234567',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Patient Details already exists! Click Search Button")

# Test the bill search POST path for both valid and invalid bill numbers
    def test_bill_search_invalid_bill_shows_message(self):
        response = self.client.post(reverse('patient_details'), {
            'billSearch': '1',
            'billNo': 'INVALID123',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please Check the Bill Number")


    def test_bill_search_valid_bill_renders_return_page(self):
        # Create a Bill object for this test
        patient = PatientDetail.objects.create(
            patientName='Bill Patient',
            patientPhoneNo='5559998888',
            patientID=f"AMC-{uuid4().hex[:8]}"
        )
        category = Category.objects.create(name='General')
        medicine = Medicine.objects.create(medicineName='Paracetamol', medCategory=category)
        procure = MedicineProcureDetails.objects.create(
            pharmacy_user=self.user,
            medicine=medicine,
            batchNo='A1',
            pack=10,
            quantity=2,
            pricePerStrip=Decimal('20'),
            mrp=Decimal('25'),
            expiryDate=timezone.now().date() + datetime.timedelta(days=365)
        )
        stock = MedicineStock.objects.get(medicine=medicine, batchNo='A1')
        bill = Bill.objects.create(
            patientID=patient,
            medStock=stock,  
            noOfTabletsOrdered=1,
            totalPrice=Decimal('10'),
            discount=0,
            discountedPrice=Decimal('10'),
            billNo='VALIDBILL',
            billDate=timezone.now(),
            transactionCompleted='N'
        )
        response = self.client.post(reverse('patient_details'), {
            'billSearch': '1',
            'billNo': 'VALIDBILL',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pharmacyapp/meds_return.html')
        self.assertContains(response, 'VALIDBILL')

# Test GET request renders form
    def test_get_request_renders_form(self):
        response = self.client.get(reverse('patient_details'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pharmacyapp/patient_details.html')
        self.assertIsInstance(response.context['form'], PatientForm)

#Permission Test
    def test_redirect_if_not_logged_in(self):
        self.client.logout()
        response = self.client.get(reverse('patient_details'))
        self.assertRedirects(response, f'/accounts/login/?next={reverse("patient_details")}')

#Integration Test: Register --> Add to Cart --> Checkout
    def test_full_patient_registration_to_checkout_flow(self):
        # Register new patient
        response = self.client.post(reverse('patient_details'), {
            'newReg': '1',
            'patientName': 'Flow Test',
            'patientPhoneNo': '9991234567',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        patient = PatientDetail.objects.get(patientPhoneNo='9991234567')

        # Setup: create category, medicine, procurement, stock
        cat = Category.objects.create(name='Flow')
        med = Medicine.objects.create(medicineName='TestMed', medCategory=cat)
        procurement = MedicineProcureDetails.objects.create(
            pharmacy_user=self.user,
            medicine=med,
            batchNo='F123',
            pack=10,
            quantity=5,
            pricePerStrip=Decimal('100'),
            mrp=Decimal('100'),
            expiryDate=timezone.now().date() + datetime.timedelta(days=180)
        )
        stock = MedicineStock.objects.get(medicine=med, batchNo='F123')

        # Add medicine to Bill (cart)
        bill = Bill.objects.create(
            patientID=patient,
            medStock=stock,
            noOfTabletsOrdered=5,
            totalPrice=Decimal('50'),
            discount=0,
            discountedPrice=Decimal('50'),
            billNo='FLOW-123',
            billDate=timezone.now(),
            transactionCompleted='N'
        )

        # Checkout
        checkout_url = reverse('medicine_checkout', args=[patient.pk])
        response = self.client.post(checkout_url, follow=True)
        self.assertEqual(response.status_code, 200)
        bill.refresh_from_db()
        self.assertEqual(bill.transactionCompleted, 'Y')
        self.assertEqual(MedicineStock.objects.get(pk=stock.pk).noOfTabletsInStore, 45)
        self.assertTrue(Sale.objects.filter(stock=stock).exists())
