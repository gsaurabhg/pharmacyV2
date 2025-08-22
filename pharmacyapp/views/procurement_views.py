from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from pharmacyapp.models import Category, Medicine, MedicineProcureDetails, MedicineStock


@login_required
def procurement_form(request):
    current_user = request.user.username
    allowed_users = ["admin", "saurabhg", "gaurav", "meenu"]

    if current_user not in allowed_users:
        messages.info(request, "You must be logged in as an ADMIN to add new products.")
        return render(request, 'pharmacyapp/popup.html')

    categories = Category.objects.all()
    today = timezone.now().date()

    if request.method == 'POST':
        form_data = request.POST

        # Extract form data
        medicine_name = form_data.get('medicineName')
        med_category_id = form_data.get('medCategory')
        batch_no = form_data.get('batchNo')
        pack = int(form_data.get('pack', 0))
        quantity = int(form_data.get('quantity', 0))
        price_per_strip = float(form_data.get('pricePerStrip', 0))
        mrp = float(form_data.get('mrp', 0))
        date_of_purchase = form_data.get('dateOfPurchase')
        expiry_date = form_data.get('expiryDate')

        # Convert dates
        try:
            date_of_purchase = timezone.datetime.strptime(date_of_purchase, '%Y-%m-%d').date()
            expiry_date = timezone.datetime.strptime(expiry_date, '%Y-%m-%d').date()
        except Exception:
            messages.error(request, "Invalid date format.")
            return render(request, 'pharmacyapp/procurement_form.html', {'categories': categories, 'form_data': form_data})

        # Validations
        if expiry_date <= date_of_purchase:
            messages.error(request, "Expiry date must be after the date of purchase.")
            return render(request, 'pharmacyapp/procurement_form.html', {'categories': categories, 'form_data': form_data})

        if pack <= 0 or quantity <= 0 or price_per_strip <= 0 or mrp <= 0:
            messages.error(request, "All numeric fields must be greater than zero.")
            return render(request, 'pharmacyapp/procurement_form.html', {'categories': categories, 'form_data': form_data})

        # Fetch category
        try:
            category = Category.objects.get(id=med_category_id)
        except Category.DoesNotExist:
            messages.error(request, "Invalid category selected.")
            return render(request, 'pharmacyapp/procurement_form.html', {'categories': categories, 'form_data': form_data})

        # Save data inside atomic block
        try:
            with transaction.atomic():
                # Check for existing medicine with different category
                existing_medicine = Medicine.objects.filter(medicineName=medicine_name).first()
                if existing_medicine and existing_medicine.medCategory != category:
                    messages.error(
                        request,
                        f"The medicine '{medicine_name}' is already associated with the category '{existing_medicine.medCategory.name}'."
                    )
                    return render(request, 'pharmacyapp/procurement_form.html', {'categories': categories, 'form_data': form_data})

                # Create or fetch medicine
                medicine, _ = Medicine.objects.get_or_create(
                    medicineName=medicine_name,
                    medCategory=category
                )

                # Create procurement record
                MedicineProcureDetails.objects.create(
                    medicine=medicine,
                    pack=pack,
                    quantity=quantity,
                    pricePerStrip=price_per_strip,
                    mrp=mrp,
                    dateOfPurchase=date_of_purchase,
                    expiryDate=expiry_date,
                    pharmacy_user=request.user,
                    batchNo=batch_no
                )

                messages.success(request, "Procurement details saved successfully.")
                return redirect('procurement_form')

        except Exception as e:
            messages.error(request, f"Error occurred: {str(e)}")
            return render(request, 'pharmacyapp/procurement_form.html', {'categories': categories, 'form_data': form_data})

    return render(request, 'pharmacyapp/procurement_form.html', {'categories': categories, 'today': today})


@login_required
def get_pack_size(request):
    """
    API to retrieve pack size, MRP and expiry for a given medicine + batch.
    Used in dynamic procurement UI.
    """
    medicine_name = request.GET.get('medicineName')
    batch_no = request.GET.get('batchNo')

    try:
        stock = MedicineStock.objects.get(
            medicine__medicineName=medicine_name,
            batchNo=batch_no
        )
        return JsonResponse({
            'success': True,
            'pack_size': stock.procurement.pack,
            'mrp': stock.procurement.mrp,
            'expiry_date': stock.procurement.expiryDate.strftime('%Y-%m-%d')
        })

    except MedicineStock.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'No matching record found for this medicine and batch number.'})
