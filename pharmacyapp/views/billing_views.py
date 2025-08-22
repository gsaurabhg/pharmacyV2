from decimal import Decimal
from datetime import date
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import ObjectDoesNotExist
from django.utils.crypto import get_random_string
from django.contrib.auth.decorators import login_required

from pharmacyapp.models import PatientDetail, MedicineStock, Bill, Sale
from pharmacyapp.forms import availableMedsForm


@login_required
def bill_details(request, pk):
    record = get_object_or_404(PatientDetail, pk=pk)
    bill_items = Bill.objects.filter(patientID__patientID=record.patientID, transactionCompleted='N')

    if not bill_items:
        messages.info(request, "Please check!! Nothing in Cart")
        return render(request, 'pharmacyapp/bill_details.html', {'record': record})

    return render(request, 'pharmacyapp/med_checkout.html', {'billGeneration': bill_items})


@login_required
def medicine_order(request, pk):
    patient = get_object_or_404(PatientDetail, pk=pk)
    today = date.today()

    # Fetch available medicines
    stocks = MedicineStock.objects.filter(
        noOfTabletsInStore__gt=0,
        procurement__expiryDate__gt=today
    ).select_related('procurement__medicine').order_by('procurement__medicine__medicineName')

    medicine_choices = list({
        (stock.procurement.medicine.medicineName, stock.procurement.medicine.medicineName)
        for stock in stocks
    })

    form = availableMedsForm(medicine_choices)

    if request.method == "POST":
        form_data = request.POST
        med_name = form_data.get('medicineName')
        batch_no = form_data.get('batchNo')
        qty = form_data.get('orderQuantity')
        discount = int(form_data.get('discount', 0))

        if form_data.get('addMed'):
            if not all([med_name, batch_no, qty]):
                messages.info(request, "Please fill all required fields")
                return render(request, 'pharmacyapp/medicine_order.html', {'form': form, 'webFormFields': form_data})

            qty = int(qty)
            if qty <= 0:
                messages.info(request, "Please provide valid quantity of medicines")
                return render(request, 'pharmacyapp/medicine_order.html', {'form': form, 'webFormFields': form_data})

            try:
                stock = MedicineStock.objects.get(medicine__medicineName=med_name, batchNo=batch_no)
            except MedicineStock.DoesNotExist:
                messages.info(request, "Medicine or batch number not found.")
                return render(request, 'pharmacyapp/medicine_order.html', {'form': form, 'webFormFields': form_data})

            if qty > stock.noOfTabletsInStore:
                messages.info(request, f"Quantity exceeds available stock of {stock.noOfTabletsInStore}")
                return render(request, 'pharmacyapp/medicine_order.html', {'form': form, 'webFormFields': form_data})

            existing_entry = Bill.objects.filter(
                patientID__patientID=patient.patientID,
                medStock=stock,
                transactionCompleted='N'
            ).first()

            if existing_entry:
                existing_entry.noOfTabletsOrdered += qty
                if existing_entry.noOfTabletsOrdered > stock.noOfTabletsInStore:
                    messages.info(request, f"Combined quantity exceeds available stock of {stock.noOfTabletsInStore}")
                    return render(request, 'pharmacyapp/medicine_order.html', {'form': form, 'webFormFields': form_data})

                existing_entry.totalPrice = existing_entry.noOfTabletsOrdered * stock.procurement.pricePerTablet
                existing_entry.discountedPrice = (Decimal(1) - Decimal(discount) / 100) * existing_entry.totalPrice
                existing_entry.discount = discount
                existing_entry.save()
            else:
                # Remove orphan entries without billNo
                Bill.objects.filter(patientID=patient, transactionCompleted='N', billNo__isnull=True).delete()

                # Check for existing bill number
                existing_bill = Bill.objects.filter(patientID=patient, transactionCompleted='N').first()
                if existing_bill:
                    bill_no = existing_bill.billNo
                    bill_date = existing_bill.billDate
                else:
                    bill_no = f"SSDS-{timezone.now().strftime('%Y%m%d-%H%M%S')}-{get_random_string(4).upper()}"
                    bill_date = timezone.now()

                # Create new bill entry
                Bill.objects.create(
                    patientID=patient,
                    medStock=stock,
                    noOfTabletsOrdered=qty,
                    totalPrice=qty * stock.procurement.pricePerTablet,
                    discountedPrice=(Decimal(1) - Decimal(discount) / 100) * qty * stock.procurement.pricePerTablet,
                    discount=discount,
                    transactionCompleted='N',
                    billNo=bill_no,
                    billDate=bill_date
                )

            messages.success(request, "Added medicine to cart.")
            return render(request, 'pharmacyapp/medicine_order.html', {'form': form})

        elif form_data.get('order'):
            bill_items = Bill.objects.filter(patientID=patient, transactionCompleted='N')
            if bill_items.exists():
                return render(request, 'pharmacyapp/med_checkout.html', {'billGeneration': bill_items})
            messages.info(request, "Nothing in Cart")
            return render(request, 'pharmacyapp/medicine_order.html', {'form': form})

    return render(request, 'pharmacyapp/medicine_order.html', {'form': form})


@login_required
def medicine_checkout(request, pk):
    patient = get_object_or_404(PatientDetail, pk=pk)
    bills = Bill.objects.filter(patientID__patientID=patient.patientID, transactionCompleted='N').select_related('medStock', 'medStock__medicine', 'medStock__procurement')

    if not bills:
        messages.info(request, "No pending bills found.")
        return render(request, 'pharmacyapp/med_checkout.html')

    try:
        with transaction.atomic():
            for bill in bills:
                if bill.noOfTabletsOrdered > bill.medStock.noOfTabletsInStore:
                    messages.error(request, f"Insufficient stock for {bill.medStock.medicine.medicineName} (Batch: {bill.medStock.batchNo})")
                    return render(request, 'pharmacyapp/med_checkout.html', {'billGeneration': bills})

            for bill in bills:
                Sale.objects.create(
                    medicine=bill.medStock.medicine,
                    stock=bill.medStock,
                    noOfTabletsSold=bill.noOfTabletsOrdered
                )
                bill.transactionCompleted = 'Y'
                bill.save()

        messages.success(request, "Checkout successful. Final bill generated.")
        return redirect('final_bill_view', bill_no=bills[0].billNo)

    except Exception as e:
        messages.error(request, f"Error during checkout: {str(e)}")
        return render(request, 'pharmacyapp/med_checkout.html', {'billGeneration': bills})


@login_required
def final_bill_view(request, bill_no):
    bill_items = Bill.objects.filter(billNo=bill_no)
    if not bill_items:
        messages.error(request, "Invalid or expired bill reference.")
        return redirect('patient_details')

    return render(request, 'pharmacyapp/final_bill.html', {'billGeneration': bill_items})


@login_required
def medicine_last_checkout(request, pk):
    patient = get_object_or_404(PatientDetail, pk=pk)
    try:
        latest_bill = Bill.objects.filter(patientID__patientID=patient.patientID, transactionCompleted='Y').latest('pk')
    except ObjectDoesNotExist:
        messages.info(request, "First-time customer. No previous invoice found.")
        return redirect('patient_details')

    final_bill_items = Bill.objects.filter(billNo=latest_bill.billNo, transactionCompleted='Y')
    return render(request, 'pharmacyapp/final_bill.html', {'billGeneration': final_bill_items})


