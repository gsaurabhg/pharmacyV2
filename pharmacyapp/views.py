from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from .models import *
from .forms import *
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
#Below import is needed for making OR based query
from django.db.models import Q, F, Count
#Below import is needed for creating the pop ups
from django.contrib import messages
from decimal import *
from datetime import date, timedelta, datetime, time
from django.core import validators
import datetime, time, json
from django.core import serializers
from django.http import HttpResponse
#needed for the pass word creae viewitems
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
import logging 
from pharmacyapp.utilities import *
#this is needed so that we can call call command fx via which we can execute any comman
from django.core.management import call_command
#this is to enable zipping
import zipfile, io, csv
from django.core.mail import EmailMessage
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from uuid import uuid4
from django.utils.crypto import get_random_string


logging.basicConfig(filename="log.log", level=logging.DEBUG)

def welcome(request):
    return render(request, 'pharmacyapp/popup.html')


def inventory_list(request):
    # Get all categories from the Category table
    categories = Category.objects.all()

    # Get active tab from GET parameter (to remember last clicked tab)
    active_tab = request.GET.get('active_tab', None)

    # Set default active tab based on user role if no tab is set in the request
    if not active_tab:
        if request.user.username == 'gaurav':  # Admin user
            active_tab = 'Urology'
        elif request.user.username == 'meenu':  # For a local user (can customize to any criteria)
            active_tab = 'Ob-Gyn'
        else:  # Default to a general category if no specific user match
            active_tab = 'General Medicine'

    # Initialize a list to store medicines for each category
    medicines = {}

    # Fetch medicines for each category dynamically
    for category in categories:
        category_name = category.name
        medicines[category_name] = MedicineStock.objects.select_related('medicine', 'procurement', 'medicine__medCategory')\
            .filter(medicine__medCategory__name=category_name)\
            .values(
                'pk',  # Primary key from MedicineStock
                'medicine__medicineName',  # Medicine name from Medicine model
                'batchNo',  # Batch number from MedicineStock
                'procurement__expiryDate',  # Expiry date from MedicineProcureDetails
                'procurement__pricePerTablet',  # Price per tablet from MedicineProcureDetails
                'noOfTabletsInStore'  # Number of tablets in stock from MedicineStock
            )

    # Query to retrieve all medicines whose stock is 0 or expired, without filtering by category
    expired_nill = MedicineStock.objects.select_related('medicine', 'procurement')\
        .filter(Q(noOfTabletsInStore=0) | Q(procurement__expiryDate__lt=timezone.now().date()))\
        .values(
            'pk',  # Primary key from MedicineStock
            'medicine__medicineName',  # Medicine name from Medicine model
            'batchNo',  # Batch number from MedicineStock
            'procurement__expiryDate',  # Expiry date from MedicineProcureDetails
            'procurement__pricePerTablet',  # Price per tablet from MedicineProcureDetails
            'noOfTabletsInStore'  # Number of tablets in stock from MedicineStock
        )

    # Prepare context for rendering the template
    context = {
        'categories': categories,  # All categories to display in the tabs
        'medicines': medicines,  # List of medicines grouped by category
        'expired_nill': expired_nill,  # Medicines that are expired or out of stock
        'active_tab': active_tab  # Tab to be highlighted based on user type
    }

    # Render the template with the context
    return render(request, 'pharmacyapp/inventory_list.html', context)

    
def med_detail(request, pk):
    stockDetail = get_object_or_404(MedicineStock, pk=pk)
    return render(request, 'pharmacyapp/med_detail.html', {'MedicineStock': stockDetail})


def today_date(request):
    return timezone.now().date()

def procurement_form(request):
    current_user = request.user.username
    if (current_user == "admin" or current_user == "saurabhg"  or current_user == "gaurav" or current_user == "meenu"):
        if request.method == 'POST':
            # Get form data
            medicine_name = request.POST.get('medicineName')
            med_category_id = request.POST.get('medCategory')
            batch_no = request.POST.get('batchNo')
            pack = int(request.POST.get('pack'))
            quantity = int(request.POST.get('quantity'))
            price_per_strip = float(request.POST.get('pricePerStrip'))
            mrp = float(request.POST.get('mrp'))
            date_of_purchase = request.POST.get('dateOfPurchase')
            expiry_date = request.POST.get('expiryDate')

            # Convert date strings to datetime objects
            date_of_purchase = timezone.datetime.strptime(date_of_purchase, '%Y-%m-%d').date()
            expiry_date = timezone.datetime.strptime(expiry_date, '%Y-%m-%d').date()

            # Ensure that expiry date is after date of purchase
            if expiry_date <= date_of_purchase:
                messages.error(request, "Expiry date must be after the date of purchase.")
                return render(request, 'pharmacyapp/procurement_form.html', {'categories': Category.objects.all(), 'form_data': request.POST})

            # Validate fields
            if pack <= 0 or quantity <= 0 or price_per_strip <= 0 or mrp <= 0:
                messages.error(request, "All fields must be positive values.")
                return render(request, 'pharmacyapp/procurement_form.html', {'categories': Category.objects.all(), 'form_data': request.POST})

            # Fetch the selected category
            try:
                category = Category.objects.get(id=med_category_id)
            except Category.DoesNotExist:
                messages.error(request, "Invalid category selected.")
                return render(request, 'pharmacyapp/procurement_form.html', {'categories': Category.objects.all(), 'form_data': request.POST})

            # Start a transaction block to ensure atomicity
            try:
                with transaction.atomic():
                    # Check if the medicine name already exists with a different category
                    existing_medicine = Medicine.objects.filter(medicineName=medicine_name).first()

                    if existing_medicine:
                        # Check if the category of the existing medicine is different
                        if existing_medicine.medCategory != category:
                            messages.error(request, f"The medicine '{medicine_name}' is already associated with the category '{existing_medicine.medCategory.name}'. Please select the correct category or edit the existing record.")
                            return render(request, 'pharmacyapp/procurement_form.html', {'categories': Category.objects.all(), 'form_data': request.POST})

                    # If no issues, create or get the medicine record
                    medicine, created = Medicine.objects.get_or_create(
                        medicineName=medicine_name,
                        medCategory=category
                    )

                    # Create a new procurement record
                    procurement = MedicineProcureDetails.objects.create(
                        medicine=medicine,
                        pack=pack,
                        quantity=quantity,
                        pricePerStrip=price_per_strip,
                        mrp=mrp,
                        dateOfPurchase=date_of_purchase,
                        expiryDate=expiry_date,
                        pharmacy_user=request.user,  # Assuming the logged-in user is the one making the procurement
                        batchNo=batch_no
                    )
                    # Stock update is automatically handled in MedicineProcureDetails.save()
                    # Success message
                    messages.success(request, "Procurement details have been saved successfully.")
                    return redirect('procurement_form')
            except Exception as e:
                        # If any error happens in the atomic block, the transaction will be rolled back
                        messages.error(request, f"Error occurred: {str(e)}")
                        return render(request, 'procurement_form.html', {'categories': categories, 'form_data': request.POST})

        else:
            categories = Category.objects.all()  # Fetch categories from the database
            today = today_date(request)  # Get today's date for the calendar widget
            return render(request, 'pharmacyapp/procurement_form.html', {'categories': categories, 'today': today})
    else:
        messages.info(request,"You have to LOG in as ADMIN to add new Products")
        return render(request, 'pharmacyapp/popup.html')

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

@login_required
def med_delete(request, pk,active_tab):
    med = get_object_or_404(MedicineStock, pk=pk)
    medName=med.medicine.medicineName
    med.delete()
    messages.info(request,"Medicine: "+medName+" Deleted from the records")
    # Redirect to inventory list with the active_tab preserved
    url = reverse('inventory_list') + f'?active_tab={active_tab}'
    return redirect(url)

@login_required    
def patient_details(request):
    if request.method == "POST":
        form = PatientForm(request.POST)
        patientNameToSearch = request.POST.get('patientName')
        patientIDToSearch = request.POST.get('patientID')
        patientPhoneNoToSearch = request.POST.get('patientPhoneNo')
        
        if request.POST.get('search'):
            query = Q()
            if patientNameToSearch:
                query |= Q(patientName__icontains=patientNameToSearch)
            if patientIDToSearch:
                query |= Q(patientID__iexact=patientIDToSearch)
            if patientPhoneNoToSearch:
                query |= Q(patientPhoneNo__iexact=patientPhoneNoToSearch)
            if not query:
                messages.info(request, "Enter one of the fields")
                return redirect('patient_details')
            patientRecord = PatientDetail.objects.filter(query)
            return render(request, 'pharmacyapp/patient_search_results.html', {'patientRecord': patientRecord})  

            #####MAKE THE BILL FORM IN 2 FRAMES
        if request.POST.get('newReg'):
            if patientPhoneNoToSearch == "":
                messages.info(request, "Enter Phone Number")
                return render(request, 'pharmacyapp/patient_details.html', {'form': form})
            existingRecordFound = PatientDetail.objects.filter(patientName__contains=patientNameToSearch,patientPhoneNo__exact = patientPhoneNoToSearch)
            if existingRecordFound:
                messages.info(request, "Patient Details already exists! Click Search Button")
                return render(request, 'pharmacyapp/patient_details.html', {'form': form})
            patientDetail = form.save(commit=False)
            patientDetail.patientID = f"AMC-{uuid4().hex[:8].upper()}"
            patientDetail.save()
            return redirect('bill_details', pk=patientDetail.pk)
            #####MAKE THE BILL FORM IN 2 FRAMES
        if request.POST.get('billSearch'):
            webFormFields = request.POST
            bill_No = webFormFields['billNo'].upper()
            billDet = Bill.objects.filter(billNo=bill_No)
            if len(billDet) == 0:
                messages.info(request,"Please Check the Bill Number")
            else:
                return render(request, 'pharmacyapp/meds_return.html', {'billDet':billDet})
    else:
        form = PatientForm()
    return render(request, 'pharmacyapp/patient_details.html', {'form': form})

def patient_queue(request):
    form = PatientQueueForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        patient = form.cleaned_data['patient']
        
        # Check if the patient is already in queue and not yet served
        already_in_queue = PatientQueueEntry.objects.filter(patient=patient, is_served=False).exists()
        
        if already_in_queue:
            messages.warning(request, f"{patient.patientName} is already in the queue.")
        else:
            PatientQueueEntry.objects.create(patient=patient)
            messages.success(request, f"{patient.patientName} added to queue.")
        
        return redirect('patient_queue')

    queue = PatientQueueEntry.objects.filter(is_served=False)
    served = PatientQueueEntry.objects.filter(is_served=True)

    context = {
        'form': form,
        'queue': queue,
        'served': served,
    }
    return render(request, 'pharmacyapp/patient_queue.html', context)


def serve_patient(request, entry_id):
    entry = get_object_or_404(PatientQueueEntry, id=entry_id)
    entry.mark_served()
    messages.success(request, f"{entry.patient.patientName} has been marked as served.")
    return redirect('patient_queue')

def clear_served_patients(request):
    if request.method == 'POST':
        PatientQueueEntry.objects.filter(is_served=True).delete()
    return redirect('patient_queue')  # update with your queue view name
    
@login_required    
def bill_details(request, pk):
    record = get_object_or_404(PatientDetail, pk=pk)
    billGeneration = Bill.objects.filter(patientID__patientID__exact = record.patientID,transactionCompleted__exact = 'N')
    if len(billGeneration) == 0:
        messages.info(request, "Pls check !! Nothing in Cart")            
        return render(request, 'pharmacyapp/bill_details.html', {'record': record})
    else:
        return render(request, 'pharmacyapp/med_checkout.html',{'billGeneration': billGeneration})


@login_required    
def medicine_order(request, pk):
    patientDetails = get_object_or_404(PatientDetail, pk=pk)
    # Get today's date
    today = date.today()
    
    # Query to fetch medicines with stock greater than 0 and expiry date greater than today, ordered by medicine name
    medicines_in_stock = MedicineStock.objects.filter(
        noOfTabletsInStore__gt=0,  # Tablets in store greater than 0
        procurement__expiryDate__gt=today  # Expiry date is greater than today's date
        ).select_related('procurement__medicine').order_by('procurement__medicine__medicineName')

    medicineNameChoices = list({(stock.procurement.medicine.medicineName, stock.procurement.medicine.medicineName) for stock in medicines_in_stock})

    
    form = availableMedsForm(medicineNameChoices)
    if (request.method == "POST" and request.POST.get('addMed')):
        webFormFields = request.POST
        
        required_fields = ['medicineName', 'orderQuantity', 'batchNo']
        if any(webFormFields.get(field) in [None, ''] for field in required_fields):
            messages.info(request, "Please fill all required fields")
            return render(request, 'pharmacyapp/medicine_order.html', {'form': form, 'webFormFields': webFormFields})
       
        if (int(webFormFields['orderQuantity']) <= 0):
            messages.info(request,"Please provide valid quantity of medicines ")
            return render(request, 'pharmacyapp/medicine_order.html', {'form': form, 'webFormFields': webFormFields})
        
        # Fetch medicine stock (Optimized with exception handling)
        try:
            medicine_stock = MedicineStock.objects.get(medicine__medicineName=webFormFields['medicineName'], \
                                                       batchNo=webFormFields['batchNo'])
        except MedicineStock.DoesNotExist:  # Handling if no matching stock is found, Ideally it wont hit this except.
            messages.info(request, "Medicine or batch number not found.")
            return render(request, 'pharmacyapp/medicine_order.html', {'form': form, 'webFormFields': webFormFields})
                                                        
        if Decimal(webFormFields['orderQuantity']) > medicine_stock.noOfTabletsInStore:
            messages.info(request, f"Quantity of {webFormFields['medicineName']} exceeds available stock of \
                                                    {medicine_stock.noOfTabletsInStore}")
            messages.info(request,"Reach Out to Admin for ordering more medicine in Pharmacy")
            return render(request, 'pharmacyapp/medicine_order.html', {'form': form, 'webFormFields': webFormFields})
            
        # Check if this medicine is already in the cart (bill for the patient)
        existing_entry = Bill.objects.filter(
            patientID__patientID=patientDetails.patientID,
            medStock=medicine_stock,
            transactionCompleted='N'
        ).first()

        if existing_entry:
            # Update existing entry instead of creating a new one, but before that check for the quantity in the stores
            existing_entry.noOfTabletsOrdered += int(webFormFields['orderQuantity'])
            if existing_entry.noOfTabletsOrdered > medicine_stock.noOfTabletsInStore:
                messages.info(request, f"You had prevously added {webFormFields['medicineName']} and combined quantity \
                                                        exceeds available stock of {medicine_stock.noOfTabletsInStore}.\n")
                messages.info(request,"Reach Out to Admin for ordering more medicine in Pharmacy")
                return render(request, 'pharmacyapp/medicine_order.html', {'form': form, 'webFormFields': webFormFields})

            existing_entry.totalPrice = existing_entry.noOfTabletsOrdered * medicine_stock.procurement.pricePerTablet
            existing_entry.discountedPrice = (Decimal(1) - (Decimal(webFormFields['discount']) / Decimal(100))) * existing_entry.noOfTabletsOrdered * medicine_stock.procurement.pricePerTablet
            existing_entry.discount = int(webFormFields['discount'])
            existing_entry.save()
        else:        
            #Creating the new database entry for storing bill information
            billDetails = Bill(patientID=patientDetails)
            billDetails.medStock = medicine_stock
            billDetails.noOfTabletsOrdered = int(webFormFields['orderQuantity'])
            billDetails.totalPrice = Decimal(webFormFields['orderQuantity'])*medicine_stock.procurement.pricePerTablet
            billDetails.discount = int(webFormFields['discount'])
            billDetails.discountedPrice = (Decimal(1)-(Decimal(webFormFields['discount'])/Decimal(100)))*Decimal(webFormFields['orderQuantity'])*medicine_stock.procurement.pricePerTablet
            billDetails.transactionCompleted = 'N'
        
            # We check if there are any incomplete previous bills. When medicines are added for the first time for a 
            # specific patient, we enter "IF"  block and generate a bill number. Subsequent additions won’t trigger 
            # this block. If a patient decides not to take the medicines, and a new patient comes in, this block ensures 
            # any pending bills are deleted before generating a new bill number."
            Bill.objects.filter(patientID=patientDetails, transactionCompleted='N', billNo__isnull=True).delete()
            
            unSettledRecord = Bill.objects.filter(patientID=patientDetails, transactionCompleted='N').first()
            if not unSettledRecord:
                # No active bill exists — generate a new bill number
                new_bill_no = f"SSDS-{timezone.now().strftime('%Y%m%d-%H%M%S')}-{get_random_string(4).upper()}"
                billDetails.billNo = new_bill_no
                billDetails.billDate = timezone.now()
            else:
                # Reuse the existing bill number and date
                billDetails.billNo = unSettledRecord.billNo
                billDetails.billDate = unSettledRecord.billDate
            # Save the new bill line item (whether new bill or appended to existing one)
            billDetails.save()

        messages.info(request,"Added medicine in Cart")
        return render(request, 'pharmacyapp/medicine_order.html', {'form': form})
        
    elif (request.method == "POST" and request.POST.get('order')):
        billGeneration = Bill.objects.filter(patientID__patientID = patientDetails.patientID,transactionCompleted = 'N')
        if billGeneration.exists() :
            return render(request, 'pharmacyapp/med_checkout.html',{'billGeneration': billGeneration})
        else:
            messages.info(request, "Nothing in Cart")            
            return render(request, 'pharmacyapp/medicine_order.html', {'form': form})
    return render(request, 'pharmacyapp/medicine_order.html', {'form': form})

@login_required
def medicine_checkout(request, pk):
    patientInfo = get_object_or_404(PatientDetail, pk=pk)
    billGeneration = Bill.objects.filter(
        patientID__patientID=patientInfo.patientID,
        transactionCompleted='N'
    ).select_related('medStock', 'medStock__medicine', 'medStock__procurement')

    if not billGeneration.exists():
        messages.info(request, "No pending bills found.")
        return render(request, 'pharmacyapp/med_checkout.html', {})

    try:
        with transaction.atomic():
            # 1. Validate stock availability before any changes
            for billDetail in billGeneration:
                if billDetail.noOfTabletsOrdered > billDetail.medStock.noOfTabletsInStore:
                    messages.error(
                        request,
                        f"Insufficient stock for {billDetail.medStock.medicine.medicineName} (Batch: {billDetail.medStock.batchNo})."
                    )
                    return render(request, 'pharmacyapp/med_checkout.html', {'billGeneration': billGeneration})

            # 2. Process each item: deduct stock, create Sale, mark bill completed
            for billDetail in billGeneration:
                stock = billDetail.medStock  # MedicineStock object
                medicine = stock.medicine
                quantity = billDetail.noOfTabletsOrdered

                # Create and save Sale entry (this will deduct stock)
                sale_entry = Sale(
                    medicine=medicine,
                    stock=stock,
                    noOfTabletsSold=quantity
                )
                sale_entry.save()  # This will trigger  custom save() logic

                # Mark bill item as completed
                billDetail.transactionCompleted = 'Y'
                billDetail.save()

    except Exception as e:
        messages.error(request, f"An error occurred while finalizing the bill: {str(e)}")
        return render(request, 'pharmacyapp/med_checkout.html', {'billGeneration': billGeneration})

    # Optional: Pass bill number or data to final_bill template for PDF generation
    #passing the bill no to generate the pdf
    #generate_pdf(billGeneration[0].billNo)
    messages.success(request, "Checkout successful. Final bill generated.")
    return redirect('final_bill_view', bill_no=billGeneration[0].billNo)
    
@login_required
def final_bill_view(request, bill_no):
    billGeneration = Bill.objects.filter(billNo=bill_no)
    if not billGeneration.exists():
        messages.error(request, "Invalid or expired bill reference.")
        return redirect('pharmacyapp:medicine_order')  

    return render(request, 'pharmacyapp/final_bill.html', {'billGeneration': billGeneration})
    
@login_required    
def medicine_last_checkout(request, pk):
    patientInfo = get_object_or_404(PatientDetail, pk=pk)
    #To fix the use case of first entry
    try:
        billGeneration = Bill.objects.filter(patientID__patientID__exact = patientInfo.patientID,transactionCompleted__exact = 'Y').latest('pk')
    except ObjectDoesNotExist :
        messages.info(request,"This is the first time Customer, so no previous Invoice found")
        return redirect('patient_details')
    billGeneration = Bill.objects.filter(billNo__exact = billGeneration.billNo,transactionCompleted__exact = 'Y')
    return render(request, 'pharmacyapp/final_bill.html', {'billGeneration': billGeneration})
    
@login_required  
def medicine_remove(request, pk):
    billInfo = get_object_or_404(Bill,pk=pk)
    models = Bill.objects.filter(billNo = billInfo.billNo, \
                                medStock__medicine__medicineName=billInfo.medStock.medicine.medicineName, \
                                medStock__procurement__batchNo = billInfo.medStock.procurement.batchNo, \
                                patientID__patientID = billInfo.patientID.patientID, \
                                transactionCompleted__exact= 'N').delete()
    billGeneration = Bill.objects.filter(patientID__patientID__exact = billInfo.patientID.patientID, \
                                                transactionCompleted__exact = 'N')
    if billGeneration :
        return render(request, 'pharmacyapp/med_checkout.html',{'billGeneration': billGeneration})
    else:
        patientDetail = PatientDetail.objects.all().filter(patientID__exact = billInfo.patientID.patientID).get()
        return redirect('bill_details', pk=patientDetail.pk)
        
def report_sales(request):
    form = ReportForm(request.POST or None)
    reports = None

    if request.method == "POST":
        # For 'custom' filter, get medicine filter
        medicine_filter = {}

        if request.POST.get('custom') and form.is_valid():
            medicine_id = form.cleaned_data['medicineName']
            if medicine_id:
                medicine_filter['medStock__medicine_id'] = medicine_id

            startdate = form.cleaned_data['startDate']
            enddate = form.cleaned_data['endDate']

            if not startdate or not enddate:
                messages.info(request, "Please enter both start and end dates.")
            elif enddate < startdate:
                messages.info(request, "End date cannot be earlier than start date.")
            else:
                reports = Bill.objects.filter(billDate__range=[startdate, enddate], transactionCompleted='Y', **medicine_filter).order_by('billNo')

        elif request.POST.get('Today'):
            startdate = enddate = date.today()
            reports = Bill.objects.filter(billDate__range=[startdate, enddate], transactionCompleted='Y').order_by('billNo')

        elif request.POST.get('Yesterday'):
            startdate = enddate = date.today() - timedelta(days=1)
            reports = Bill.objects.filter(billDate__range=[startdate, enddate], transactionCompleted='Y').order_by('billNo')

    return render(request, 'pharmacyapp/report_sales.html', {'form': form, 'reports': reports})

def report_purchases(request):
    form = PurchaseReportForm(request.POST or None)
    reports = MedicineProcureDetails.objects.none()
    total_quantity = 0
    total_tablets = 0
    total_cost = 0

    if request.method == 'POST':
        if form.is_valid():
            start_date = form.cleaned_data.get('startDate')
            end_date = form.cleaned_data.get('endDate')
            medicine = form.cleaned_data.get('medicineName')
            batch_no = form.cleaned_data.get('batchNo')

            reports = MedicineProcureDetails.objects.all()
            if start_date:
                reports = reports.filter(dateOfPurchase__gte=start_date)
            if end_date:
                reports = reports.filter(dateOfPurchase__lte=end_date)
            if medicine:
                reports = reports.filter(medicine=medicine)
            if batch_no:
                reports = reports.filter(batchNo__icontains=batch_no)

            if not reports.exists():
                messages.info(request, "No matching records found.")

            # Totals
            total_quantity = sum(r.quantity for r in reports)
            total_tablets = sum(r.noOfTablets for r in reports)
            total_cost = sum(r.quantity * float(r.pricePerStrip) for r in reports)

            # Handle CSV export
            if 'export_csv' in request.POST:
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="purchase_report.csv"'

                writer = csv.writer(response)
                writer.writerow(['Date of Purchase', 'Medicine', 'Batch No', 'Quantity (Strips)', 'Pack Size', 'Total Tablets', 'Price per Strip'])

                for r in reports:
                    writer.writerow([
                        r.dateOfPurchase,
                        r.medicine.medicineName,
                        r.batchNo,
                        r.quantity,
                        r.pack,
                        r.noOfTablets,
                        r.pricePerStrip
                    ])

                writer.writerow([])
                writer.writerow(['TOTAL', '', '', total_quantity, '', total_tablets, f'{total_cost:.2f}'])

                return response

    context = {
        'form': form,
        'reports': reports,
        'total_quantity': total_quantity,
        'total_tablets': total_tablets,
        'total_cost': round(total_cost, 2)
    }
    return render(request, 'pharmacyapp/report_purchases.html', context)

def report_returns(request):
    form = ReportForm(request.POST or None)
    reports = None

    if request.method == "POST":
        medicine_filter = {}

        if request.POST.get('custom') and form.is_valid():
            medicine_id = form.cleaned_data['medicineName']
            if medicine_id:
                medicine_filter['medStock__medicine_id'] = medicine_id

            startdate = form.cleaned_data['startDate']
            enddate = form.cleaned_data['endDate']

            if not startdate or not enddate:
                messages.info(request, "Please enter both start and end dates.")
            elif enddate < startdate:
                messages.info(request, "End date cannot be earlier than start date.")
            else:
                reports = Bill.objects.filter(returnSalesBillDate__range=[startdate, enddate], returnSales='Y', **medicine_filter).order_by('billNo')

        elif request.POST.get('Today'):
            startdate = enddate = date.today()
            reports = Bill.objects.filter(returnSalesBillDate__range=[startdate, enddate], returnSales='Y').order_by('billNo')

        elif request.POST.get('Yesterday'):
            startdate = enddate = date.today() - timedelta(days=1)
            reports = Bill.objects.filter(returnSalesBillDate__range=[startdate, enddate], returnSales='Y').order_by('billNo')

    return render(request, 'pharmacyapp/report_returns.html', {'form': form, 'reports': reports})


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

from django.http import JsonResponse

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
   

@login_required
def dump_database_view(request):
    current_user = request.user.username
    if current_user in ["admin", "saurabhg"]:
        if request.method == 'POST':
            filename = request.POST.get('filename')
            current_directory = os.path.dirname(os.path.abspath(__file__))  # This gets the directory of the current file
            project_root = os.path.abspath(os.path.join(current_directory, os.pardir, os.pardir))
            zip_path = os.path.join(project_root, f"{filename}.zip")  # Path for the zip file
            try:
                 # Create an in-memory file-like buffer
                output_buffer = io.StringIO()
                call_command(
                    'dumpdata',
                    indent=2,  # equivalent to --indent 2
                    exclude=[
                        'auth.permission',               # equivalent to --exclude auth.permission
                        'contenttypes.ContentType',      # equivalent to --exclude contenttypes.ContentType
                        'admin.logentry',                # equivalent to --exclude admin.logentry
                        'sessions.session'                # equivalent to --exclude sessions.session
                    ],
                    stdout=output_buffer                  # Redirect output to the file
                )
                # Get the string data from the buffer
                json_data = output_buffer.getvalue()
                
                # Create a zip file
                with zipfile.ZipFile(zip_path, 'w') as zip_file:
                    zip_file.writestr(f"{filename}.json",  json_data)  # Add the dumped JSON data to the zip
                #messages.success(request, f'Database dumped successfully to: {zip_path}')
                #messages.info(request, f'Database dump created successfully and stored at {zip_path}.')
                return render(request, 'pharmacyapp/confirm_email.html', {'zip_path': zip_path, 'filename': filename})
                
            except Exception as e:
                messages.error(request, f'Error dumping database: {str(e)}')
    else:
        messages.info(request,"Operation Not allowed")
    return redirect('welcome')
    
def send_email_view(request):
    if request.method == 'POST':
        zip_path = request.POST.get('zip_path')
        recipient_email = request.POST.get('recipient_email')
        email_password = request.POST.get('sender_password')

        subject = 'Database Dump'
        body = 'Please find the attached database dump.'
        email = EmailMessage(subject, body, settings.EMAIL_HOST_USER, [recipient_email])
        email.attach_file(zip_path)

        try:
            original_password = settings.EMAIL_HOST_PASSWORD  # Store the original password
            settings.EMAIL_HOST_PASSWORD = email_password  # Set to the user input
            
            email.send(fail_silently=False)
            messages.success(request, f'Database dumped and emailed successfully to: {recipient_email}')
        except Exception as e:
            messages.error(request, f'Error sending email: {str(e)}')
        finally:
            # Restore the original password in settings
            settings.EMAIL_HOST_PASSWORD = original_password
    return redirect('welcome')
    
def load_data_view(request):
    current_user = request.user.username
    if current_user in ["admin", "saurabhg"]:
        if request.method == 'POST':
            zip_file = request.FILES['zip_file']

            # Create a temporary directory to unzip the file
            temp_dir = os.path.join(settings.BASE_DIR, 'temp')
            os.makedirs(temp_dir, exist_ok=True)

            # Save the uploaded zip file
            zip_path = os.path.join(temp_dir, zip_file.name)
            with open(zip_path, 'wb+') as f:
                for chunk in zip_file.chunks():
                    f.write(chunk)

            try:
                # Unzip the file
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)

                # Get the base name of the zip file (without extension) to create the JSON file path
                json_file_name = os.path.splitext(zip_file.name)[0] + '.json'  # Change the extension to .json
                json_file_path = os.path.join(temp_dir, json_file_name)

                # Clear existing data from the database
                with transaction.atomic():
                    call_command('flush', '--no-input')  # Remove old data; use with caution

                    # Load data from the JSON file
                    call_command('loaddata', json_file_path)

                messages.success(request, 'Data loaded successfully from the zip file!')
                return redirect('welcome')  # Redirect to home page after success
            except Exception as e:
                messages.error(request, f'Error loading data: {str(e)}')
            finally:
                # Clean up temporary files
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                if os.path.exists(json_file_path):
                    os.remove(json_file_path)
            return redirect('welcome')
    else:
        messages.info(request,"Operation Not allowed")
        return redirect('welcome')
    return render(request, 'pharmacyapp/load_data.html')
