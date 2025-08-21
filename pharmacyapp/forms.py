from django import forms
from .models import *


class BillForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ['patientID', 'medStock', 'noOfTabletsOrdered']

class CombinedForm(forms.ModelForm):
    Patient_Name = forms.CharField(max_length=128, help_text="Please enter the category name.")
    Patient_Id= forms.CharField(max_length=128, help_text="To be passed from the form")
    Patient_PhoneNo= forms.CharField(max_length=128, help_text="Please enter the category name.")
    Medicine_Name = forms.ChoiceField(label="Medicine Name",initial='',widget=forms.Select(),required=True)
    class Meta:
        model = Bill
        fields = ('patientID','medStock','noOfTabletsOrdered')




class PatientForm(forms.ModelForm):
    queue_type = forms.ChoiceField(
        choices=PatientQueueEntry.QUEUE_TYPE_CHOICES,
        widget=forms.RadioSelect,
        initial='current',
        label="Add to Queue"
    )

    class Meta:
        model = PatientDetail
        fields = ['patientName', 'patientPhoneNo', 'patientAadharNumber']
    
    def clean_patientAadharNumber(self):
        aadhar = self.cleaned_data['patientAadharNumber'].upper()
        # Check if this Aadhaar already exists
        if PatientDetail.objects.filter(patientAadharNumber=aadhar).exists():
            # Instead of raising ValidationError, just mark this for view to handle
            raise forms.ValidationError("Patient detail with this Aadhaar Number already exists.")
        return aadhar


Discount= ((0,0),(5,5),(10,10))
cat = (("Select","Select"),("Ob-Gyn","Ob-Gyn"),("Urology","Urology"),("General Medicine","General Medicine"))
class availableMedsForm(forms.Form):
    def __init__(self, medicineNameChoices,*args, **kwargs):
        super(availableMedsForm, self).__init__(*args, **kwargs)
        self.fields['medicineName'].choices = medicineNameChoices
    medicineName = forms.ChoiceField(label='Medicine Name',choices=(), required=True)
    medCategory = forms.ChoiceField(label='Select Category',choices=cat, required=True)
    orderQuantity = forms.DecimalField(label='Enter the quantity', required=False)
    batchNo = forms.CharField(label='Batch Number:',max_length=128,required=True)
    discount = forms.ChoiceField(label='Discount:',choices=Discount, required=True)
    

class ReportForm(forms.Form):
    startDate = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    endDate = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    medicineName = forms.ModelChoiceField(
        queryset=Medicine.objects.all().order_by('medicineName'),
        required=False,
        empty_label="All Medicines"
    )

# Form for filtering the purchase report
class PurchaseReportForm(forms.Form):
    startDate = forms.DateField(label="Start Date", required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    endDate = forms.DateField(label="End Date", required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    medicineName = forms.ModelChoiceField(
        queryset=Medicine.objects.all(),
        required=False,
        empty_label="Select Medicine"
    )
    batchNo = forms.CharField(label="Batch Number", max_length=50, required=False)

# Form to register a patient to queue
class PatientQueueForm(forms.Form):
    patient = forms.ModelChoiceField(queryset=PatientDetail.objects.all(), label="Select Patient")


class medsAdjustForm(forms.ModelForm):
    class Meta:
        model = Bill
        exclude = ['returnSales','returnSalesBillDate']
        widgets = {
                'returnSalesNoOfTablets' : forms.TextInput(    attrs   =  {'placeholder':'Enter the number of tablets to be returned'}),
        }
        
