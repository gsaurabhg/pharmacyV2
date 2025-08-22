from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import date
from pharmacyapp.models import Category, MedicineStock
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import JsonResponse
from pharmacyapp.models import *

def inventory_list(request):
    categories = Category.objects.all()
    active_tab = request.GET.get('active_tab', None)

    if not active_tab:
        if request.user.username == 'gaurav':
            active_tab = 'Urology'
        elif request.user.username == 'meenu':
            active_tab = 'Ob-Gyn'
        else:
            active_tab = 'General Medicine'

    medicines = {}
    for category in categories:
        category_name = category.name
        medicines[category_name] = MedicineStock.objects.select_related(
            'medicine', 'procurement', 'medicine__medCategory'
        ).filter(
            medicine__medCategory__name=category_name
        ).values(
            'pk', 'medicine__medicineName', 'batchNo',
            'procurement__expiryDate', 'procurement__pricePerTablet',
            'noOfTabletsInStore'
        )

    expired_nill = MedicineStock.objects.select_related('medicine', 'procurement').filter(
        Q(noOfTabletsInStore=0) | Q(procurement__expiryDate__lt=timezone.now().date())
    ).values(
        'pk', 'medicine__medicineName', 'batchNo',
        'procurement__expiryDate', 'procurement__pricePerTablet',
        'noOfTabletsInStore'
    )

    context = {
        'categories': categories,
        'medicines': medicines,
        'expired_nill': expired_nill,
        'active_tab': active_tab
    }

    return render(request, 'pharmacyapp/inventory_list.html', context)


def med_detail(request, pk):
    stockDetail = get_object_or_404(MedicineStock, pk=pk)
    return render(request, 'pharmacyapp/med_detail.html', {'MedicineStock': stockDetail})


@login_required
def med_delete(request, pk, active_tab):
    med = get_object_or_404(MedicineStock, pk=pk)
    medName = med.medicine.medicineName
    med.delete()
    messages.info(request, "Medicine: " + medName + " Deleted from the records")
    url = reverse('inventory_list') + f'?active_tab={active_tab}'
    return redirect(url)

def get_pack_size(request):
    # Get the medicineName and batchNo from the GET request
    medicine_name = request.GET.get('medicineName')
    batch_no = request.GET.get('batchNo')
    
    try:
        # Try to find the MedicineStock entry with the given medicineName and batchNo
        stock = MedicineStock.objects.get(medicine__medicineName=medicine_name, batchNo=batch_no)
        
        # Return the pack size as a JSON response
        return JsonResponse({
            'success': True,
            'pack_size': stock.procurement.pack,
            'mrp': stock.procurement.mrp,
            'expiry_date': stock.procurement.expiryDate.strftime('%Y-%m-%d')  # Format expiry date
        })    
    except MedicineStock.DoesNotExist:
        # If no matching record is found, return an error response
        return JsonResponse({'success': False, 'message': 'No matching record found for this medicine and batch number.'})

def get_batch_no(request, medName):
    medName=medName.replace("-_____-"," ")
    # Get today's date
    today = date.today()

    # Query to get batch numbers where:
    # - noOfTabletsInStore > 0
    # - expiryDate > today
    # - medicine name matches
    batch_numbers = MedicineStock.objects.filter(
        Q(medicine__medicineName=medName), 
        Q(noOfTabletsInStore__gt=0),
        Q(procurement__expiryDate__gt=today)
    ).values_list('batchNo', flat=True)

    return JsonResponse(list(batch_numbers), safe=False)


def get_quantity(request, batchNo):
    # Get the quantity of tablets in store for the given batchNo
    try:
        quantity = MedicineStock.objects.get(batchNo=batchNo).noOfTabletsInStore
        # Return the quantity as a JSON response
        return JsonResponse({'quantity': quantity})
    except MedicineStock.DoesNotExist:
        # Handle the case when batchNo is not found in MedicineStock
        return JsonResponse({'error': 'Batch number not found'}, status=404)
        
@login_required
def medicine_remove(request, pk):
    bill_entry = get_object_or_404(Bill, pk=pk)

    Bill.objects.filter(
        billNo=bill_entry.billNo,
        medStock__medicine__medicineName=bill_entry.medStock.medicine.medicineName,
        medStock__procurement__batchNo=bill_entry.medStock.procurement.batchNo,
        patientID__patientID=bill_entry.patientID.patientID,
        transactionCompleted='N'
    ).delete()

    remaining = Bill.objects.filter(
        patientID__patientID=bill_entry.patientID.patientID,
        transactionCompleted='N'
    )

    if remaining:
        return render(request, 'pharmacyapp/med_checkout.html', {'billGeneration': remaining})

    return redirect('bill_details', pk=bill_entry.patientID.pk)

@login_required
def meds_edit(request, pk):
    billAdjust = get_object_or_404(Bill, pk=pk)
    billDet = Bill.objects.filter(billNo=billAdjust.billNo)

    if request.method == 'POST':
        meds2Return = request.POST.get('meds2Return')

        if request.POST.get('returnMeds'):
            # Validation: Empty input
            if not meds2Return:
                messages.info(request, "Enter valid number of tablets to be returned")
                return render(request, 'pharmacyapp/meds_return.html', {'billDet': billDet})

            meds2Return = int(meds2Return)

            # Validation: Already returned
            if billAdjust.returnSales == "Y":
                messages.info(request, "Medicine already returned. No more allowed")
                return render(request, 'pharmacyapp/meds_return.html', {'billDet': billDet})

            # Validation: Invalid quantity
            if meds2Return > billAdjust.noOfTabletsOrdered:
                messages.info(request, "You are returning more medicines than you bought!")
                return render(request, 'pharmacyapp/meds_return.html', {'billDet': billDet})

            if meds2Return <= 0:
                messages.info(request, "Invalid return quantity. Must be greater than zero.")
                return render(request, 'pharmacyapp/meds_return.html', {'billDet': billDet})

            # Validation: Expiry check
            expiry_date = billAdjust.medStock.procurement.expiryDate
            if expiry_date < timezone.now().date():
                messages.info(
                    request,
                    f"You are returning medicines after expiry! (Expired on {expiry_date}, Today is {timezone.now().date()})"
                )
                return render(request, 'pharmacyapp/meds_return.html', {'billDet': billDet})

            # Perform return adjustments
            billAdjust.returnSalesNoOfTablets = meds2Return
            billAdjust.returnSalesBillDate = timezone.now()
            pricePerTablet = billAdjust.medStock.procurement.pricePerTablet
            discount = Decimal(billAdjust.discount) / 100
            billAdjust.returnDiscountedPrice = Decimal(meds2Return) * pricePerTablet * (1 - discount)
            billAdjust.returnSales = 'Y'
            billAdjust.save()

            # Add returned meds back to stock
            try:
                stock = billAdjust.medStock
                stock.noOfTabletsInStore += meds2Return
                stock.save()
            except ObjectDoesNotExist:
                messages.info(request, f"Batch No {billAdjust.medStock.batchNo} not found in stock. Please inform admin.")
                logging.debug(f"Missing stock for batch: {billAdjust.medStock.batchNo}, billNo: {billAdjust.billNo}")

            billDet = Bill.objects.filter(billNo=billAdjust.billNo)
            return render(request, 'pharmacyapp/meds_return.html', {'billDet': billDet})

        elif request.POST.get('back'):
            return render(request, 'pharmacyapp/meds_return.html', {'billDet': billDet})

    return render(request, 'pharmacyapp/meds_edit.html', {'billAdjust': billAdjust})