# pharmacyapp/views/reports_views.py

from datetime import date, timedelta
from django.shortcuts import render
from django.contrib import messages
from django.utils import timezone
from pharmacyapp.models import *
from pharmacyapp.forms import ReportForm,PurchaseReportForm

def report_sales(request):
    form = ReportForm(request.POST or None)
    reports = None

    if request.method == "POST":
        # Build filter criteria
        medicine_filter = {}
        startdate = enddate = None

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
                reports = Bill.objects.filter(
                    billDate__range=[startdate, enddate],
                    transactionCompleted='Y',
                    **medicine_filter
                ).order_by('billNo')

        elif request.POST.get('Today'):
            startdate = enddate = date.today()
            reports = Bill.objects.filter(
                billDate__range=[startdate, enddate],
                transactionCompleted='Y'
            ).order_by('billNo')

        elif request.POST.get('Yesterday'):
            startdate = enddate = date.today() - timedelta(days=1)
            reports = Bill.objects.filter(
                billDate__range=[startdate, enddate],
                transactionCompleted='Y'
            ).order_by('billNo')

    return render(request, 'pharmacyapp/report_sales.html', {'form': form, 'reports': reports})

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