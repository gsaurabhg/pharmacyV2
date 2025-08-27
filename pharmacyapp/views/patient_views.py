from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from uuid import uuid4

from pharmacyapp.forms import PatientForm
from pharmacyapp.models import PatientDetail, PatientQueueEntry


@login_required
def patient_dashboard(request):
    found_patients = None
    show_register_section = False

    if request.method == 'POST':
        is_registering = 'newReg' in request.POST
        form = PatientForm(request.POST, is_registering=is_registering)
        name = request.POST.get('patientName', '').strip()
        phone = request.POST.get('patientPhoneNo', '').strip()

        if 'search' in request.POST:
            query = Q()
            # Build query only if fields are provided
            if name:
                query = Q(patientName__icontains=name)
            elif phone:
                query = Q(patientPhoneNo=phone)
            else:
                messages.warning(request, "Please enter at least one field to search.")

            if query:
                found_patients = PatientDetail.objects.filter(query)
            else:
                found_patients = PatientDetail.objects.none()

            if not found_patients.exists():
                # No match found, show register section with initial form data
                show_register_section = True
                form = PatientForm(request.POST, is_registering=True)

        elif 'newReg' in request.POST:
            # Registering new patient
            if form.is_valid():
                patient = form.save(commit=False)
                patient.patientID = f"AMC-{uuid4().hex[:8].upper()}"
                patient.save()

                queue_type = form.cleaned_data.get('queue_type')
                if queue_type:
                    PatientQueueEntry.objects.create(patient=patient, queue_type=queue_type)
                    messages.success(request, f"New patient '{patient.patientName}' registered and added to queue.")
                else:
                    messages.success(request, f"New patient '{patient.patientName}' registered (not added to queue).")

                return redirect('patient_dashboard')
            else:
                # Validation failed during registration
                show_register_section = True
                # form is already with errors and is_registering=True

    else:
        form = PatientForm()

    current_queue = PatientQueueEntry.objects.filter(is_served=False, queue_type='current')
    followup_queue = PatientQueueEntry.objects.filter(is_served=False, queue_type='followup')
    served = PatientQueueEntry.objects.filter(is_served=True)

    return render(request, 'pharmacyapp/patient_dashboard.html', {
        'form': form,
        'found_patients': found_patients,
        'show_register_section': show_register_section,
        'current_queue': current_queue,
        'followup_queue': followup_queue,
        'served': served,
    })



@login_required
def add_patient_to_queue(request):
    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        queue_type = request.POST.get(f'queue_type_{patient_id}', 'current')

        try:
            patient = PatientDetail.objects.get(id=patient_id)
        except PatientDetail.DoesNotExist:
            messages.error(request, "Selected patient does not exist.")
            return redirect('patient_dashboard')

        # Check if patient is already in ANY unserved queue
        already_in_queue = PatientQueueEntry.objects.filter(
            patient=patient, is_served=False
        ).exists()

        if already_in_queue:
            messages.warning(request, f"{patient.patientName} is already in the queue.")
        else:
            PatientQueueEntry.objects.create(patient=patient, queue_type=queue_type)
            messages.success(request, f"{patient.patientName} added to the {queue_type} queue.")

    return redirect('patient_dashboard')


@login_required
def register_patient_from_search(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        queue_type = request.POST.get('queue_type', 'current')

        if not (name and phone):
            messages.error(request, "Missing data for patient registration.")
            return redirect('patient_dashboard')

        # Check if patient with this Phone Number already exists
        existing_patient = PatientDetail.objects.filter(patientPhoneNo=phone).first()
        
        if existing_patient:
            # Check if already in any active queue
            if PatientQueueEntry.objects.filter(patient=existing_patient, is_served=False).exists():
                messages.warning(request, f"Patient '{existing_patient.patientName}' is already in a queue.")
                return redirect('patient_dashboard')
            
            # Allow adding to queue if not already in one
            if queue_type != 'none':
                PatientQueueEntry.objects.create(patient=existing_patient, queue_type=queue_type)
                messages.success(request, f"{existing_patient.patientName} added to the queue.")
            else:
                messages.info(request, f"{existing_patient.patientName} already exists and was not added to a queue.")
            return redirect('patient_dashboard')

        # No existing patient, create a new one
        patient = PatientDetail.objects.create(
            patientName=name,
            patientPhoneNo=phone,
            patientID=f"AMC-{uuid4().hex[:8].upper()}"
        )

        if queue_type != 'none':
            PatientQueueEntry.objects.create(patient=patient, queue_type=queue_type)

        messages.success(request, f"{patient.patientName} registered{' and added to queue' if queue_type != 'none' else ''}.")
        return redirect('patient_dashboard')


@login_required
def serve_patient(request, entry_id):
    entry = get_object_or_404(PatientQueueEntry, id=entry_id)
    entry.mark_served()
    messages.success(request, f"{entry.patient.patientName} has been marked as served.")
    return redirect('patient_dashboard')


@login_required
def clear_served_patients(request):
    if request.method == 'POST':
        PatientQueueEntry.objects.filter(is_served=True).delete()
        messages.success(request, "All served patients have been cleared.")
    return redirect('patient_dashboard')


@login_required
def swap_patient_queue(request, entry_id):
    entry = get_object_or_404(PatientQueueEntry, id=entry_id)

    if entry.queue_type == 'current':
        entry.queue_type = 'followup'
    else:
        entry.queue_type = 'current'

    entry.save()
    messages.success(request, f"{entry.patient.patientName} moved to {entry.queue_type} queue.")
    return redirect('patient_dashboard')


def queue_view_only(request):
    current_queue = PatientQueueEntry.objects.filter(is_served=False, queue_type='current').order_by('queued_at')
    followup_queue = PatientQueueEntry.objects.filter(is_served=False, queue_type='followup').order_by('queued_at')
    served_patients = PatientQueueEntry.objects.filter(is_served=True).order_by('-served_at')[:20]

    context = {
        'current_queue': current_queue,
        'followup_queue': followup_queue,
        'served_patients': served_patients,
    }
    return render(request, 'pharmacyapp/queue_view_only.html', context)
