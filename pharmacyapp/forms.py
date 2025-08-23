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
    class Meta:
        model = PatientDetail
        fields = ['patientName', 'patientPhoneNo', 'patientAadharNumber']

    def __init__(self, *args, **kwargs):
        self.is_registering = kwargs.pop('is_registering', False)
        super().__init__(*args, **kwargs)
        if self.is_registering:
            self.fields['patientAadharNumber'].required = True
            self.fields['patientName'].required = True
            self.fields['patientPhoneNo'].required = True
        else:
            # For search, no field is required
            for field in self.fields.values():
                field.required = False

    def clean_patientAadharNumber(self):
        aadhar = self.cleaned_data.get('patientAadharNumber', '').strip().upper()
        if self.is_registering:
            if not aadhar:
                raise forms.ValidationError("Aadhaar Number is required for new registration.")
            if PatientDetail.objects.filter(patientAadharNumber=aadhar).exists():
                raise forms.ValidationError("Patient detail with this Aadhaar Number already exists.")
        return aadhar

    def clean(self):
        cleaned_data = super().clean()
        if not self.is_registering:
            if not (cleaned_data.get('patientName') or cleaned_data.get('patientPhoneNo') or cleaned_data.get('patientAadharNumber')):
                raise forms.ValidationError("Please enter at least one field to search.")
        return cleaned_data


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
        
