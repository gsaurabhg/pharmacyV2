from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from uuid import uuid4

from pharmacyapp.forms import PatientForm
from pharmacyapp.models import PatientDetail, PatientQueueEntry, Bill


@login_required
def patient_details(request):
    if request.method == "POST":
        form = PatientForm(request.POST)
        patientNameToSearch = request.POST.get('patientName')
        patientIDToSearch = request.POST.get('patientID')
        patientPhoneNoToSearch = request.POST.get('patientPhoneNo')

        # Handle Search
        if request.POST.get('search'):
            query = Q()
            if patientNameToSearch:
                query |= Q(patientName__iexact=patientNameToSearch)
            if patientIDToSearch:
                query |= Q(patientID__iexact=patientIDToSearch)
            if patientPhoneNoToSearch:
                query |= Q(patientPhoneNo=patientPhoneNoToSearch)
            if request.POST.get('patientAadharNumber'):
                aadhaar = request.POST.get('patientAadharNumber').upper()
                query |= Q(patientAadharNumber__exact=aadhaar)

            if not query:
                messages.info(request, "Enter at least one field to search.")
                return redirect('patient_details')

            patientRecord = PatientDetail.objects.filter(query)
            return render(request, 'pharmacyapp/patient_search_results.html', {'patientRecord': patientRecord})

        # Handle New Registration
        if request.POST.get('newReg'):
            if patientPhoneNoToSearch == "":
                messages.info(request, "Enter Phone Number")
                return render(request, 'pharmacyapp/patient_details.html', {'form': form})

            existingRecordFound = PatientDetail.objects.filter(
                patientName__exact=patientNameToSearch,
                patientAadharNumber__exact=aadhaar
            )
            if existingRecordFound:
                messages.info(request, "Patient already exists. Click Search.")
                return render(request, 'pharmacyapp/patient_details.html', {'form': form})

            patientDetail = form.save(commit=False)
            patientDetail.patientID = f"AMC-{uuid4().hex[:8].upper()}"
            patientDetail.patientAadharNumber = patientDetail.patientAadharNumber.upper()
            patientDetail.save()
            return redirect('bill_details', pk=patientDetail.pk)

        # Handle Bill Search
        if request.POST.get('billSearch'):
            bill_no = request.POST.get('billNo', '').upper()
            billDet = Bill.objects.filter(billNo=bill_no)
            if not billDet:
                messages.info(request, "Please check the Bill Number")
            else:
                return render(request, 'pharmacyapp/meds_return.html', {'billDet': billDet})

    else:
        form = PatientForm()

    return render(request, 'pharmacyapp/patient_details.html', {'form': form})


@login_required
def patient_queue(request):
    existing_patients = None

    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            queue_type = form.cleaned_data.get('queue_type', 'current')

            patient = form.save(commit=False)
            patient.patientAadharNumber = patient.patientAadharNumber.upper()
            patient.patientID = f"AMC-{uuid4().hex[:8].upper()}"
            patient.save()

            PatientQueueEntry.objects.create(patient=patient, queue_type=queue_type)
            messages.success(request, f"New patient '{patient.patientName}' registered and added to {queue_type} queue.")
            return redirect('patient_queue')
        else:
            if 'patientAadharNumber' in form.errors:
                aadhar = request.POST.get('patientAadharNumber').upper()
                existing_patients = PatientDetail.objects.filter(patientAadharNumber=aadhar)
                messages.info(request, "Patient(s) with this Aadhaar number exist. Please select below or register new.")

    else:
        form = PatientForm()

    current_queue = PatientQueueEntry.objects.filter(is_served=False, queue_type='current').order_by('queued_at')
    followup_queue = PatientQueueEntry.objects.filter(is_served=False, queue_type='followup').order_by('queued_at')
    served = PatientQueueEntry.objects.filter(is_served=True)

    return render(request, 'pharmacyapp/patient_queue.html', {
        'form': form,
        'queue': current_queue,
        'followup_queue': followup_queue,
        'served': served,
        'existing_patients': existing_patients,
    })


@login_required
def add_patient_to_queue(request):
    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        queue_type_key = f'queue_type_{patient_id}'
        queue_type = request.POST.get(queue_type_key, 'current')

        try:
            patient = PatientDetail.objects.get(id=patient_id)
        except PatientDetail.DoesNotExist:
            messages.error(request, "Selected patient does not exist.")
            return redirect('patient_queue')

        already_in_queue = PatientQueueEntry.objects.filter(
            patient=patient, is_served=False, queue_type=queue_type
        ).exists()

        if already_in_queue:
            messages.warning(request, f"{patient.patientName} is already in the {queue_type} queue.")
        else:
            PatientQueueEntry.objects.create(patient=patient, queue_type=queue_type)
            messages.success(request, f"{patient.patientName} added to the {queue_type} queue.")

    return redirect('patient_queue')


@login_required
def serve_patient(request, entry_id):
    entry = get_object_or_404(PatientQueueEntry, id=entry_id)
    entry.mark_served()
    messages.success(request, f"{entry.patient.patientName} has been marked as served.")
    return redirect('patient_queue')


@login_required
def clear_served_patients(request):
    if request.method == 'POST':
        PatientQueueEntry.objects.filter(is_served=True).delete()
        messages.success(request, "Cleared all served patients.")
    return redirect('patient_queue')

@login_required
def swap_patient_queue(request, entry_id):
    entry = get_object_or_404(PatientQueueEntry, id=entry_id, is_served=False)

    if entry.queue_type == 'current':
        entry.queue_type = 'followup'
    else:
        entry.queue_type = 'current'

    entry.save()
    messages.success(request, f"{entry.patient.patientName} moved to {entry.queue_type} queue.")
    return redirect('patient_queue')
