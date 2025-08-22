#pip install PyPDF2
#pip install reportlab


import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from PyPDF2 import PdfReader, PdfWriter
from django.shortcuts import render
from django.utils import timezone


from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import fonts

from pharmacyapp.models import *




def merge_pdf(existing_pdf_path, pdf_to_append_path):
  existing_pdf = open(existing_pdf_path, "rb")
  existing_pdf_reader = PdfReader(existing_pdf)

  # Create PdfWriter object to hold combined content
  writer = PdfWriter()

  # Append pages from existing PDF
  for page in existing_pdf_reader.pages:
    writer.add_page(page)

  # Open PDF to append
  pdf_to_append = open(pdf_to_append_path, "rb")
  pdf_to_append_reader = PdfReader(pdf_to_append)

  # Append pages from PDF to append
  for page in pdf_to_append_reader.pages:
    writer.add_page(page)

  # Write combined content to existing PDF file
  with open(pdf_to_append_path, "wb") as output_pdf:
    writer.write(output_pdf)

  # Close files
  existing_pdf.close()
  pdf_to_append.close()
  os.remove(existing_pdf_path)

def generate_pdf(bill_no):
  # Query the data using Django ORM
  billGeneration = Bill.objects.filter(billNo__exact=bill_no)

  # Define the name of the PDF file
  pdf_file = "./bills/"+bill_no+".pdf"
  output = open(pdf_file, "wb")

  # Extract data from the queryset
  total=0
  data = [["Medicines", "Batch Number", "Expiry Date", "Unit Prise", "Quantity", "Price", "Discounted Price"]]  # Initialize with headers
  for obj in billGeneration:
      row = [obj.medicineName, obj.batchNo, obj.expiryDate,obj.pricePerTablet,obj.noOfTabletsOrdered,obj.totalPrice,obj.discountedPrice]
      total=total+obj.totalPrice
      data.append(row)

  #append the total bill value
  row= ["Total","","","","","",total]
  data.append(row)

  # Create PDF document
  doc = SimpleDocTemplate(output, pagesize=letter, mode='a')  # 'a' for append mode
  elements = []

  # Add heading
  styles = getSampleStyleSheet()
  heading_style = ParagraphStyle(name='Heading1', parent=styles['Heading1'], alignment=1)  # 1 = Center alignment
  heading = Paragraph("<b>Shree Sai Drug Shop</b>", heading_style)
  elements.append(heading)

  heading_style = ParagraphStyle(name='Heading2', parent=styles['Heading2'], alignment=2)  # 2 = Right alignment
  heading = Paragraph("<b>C1, Vikram Colony, Aligarh, Ph.:0571-2972424</b>", heading_style)
  elements.append(heading)

  # Add line separator 
  elements.append(Spacer(1, 12))  # Add some space after heading
  #---> error in next line?
  #elements.append(Line(0, 0, 530, 0))  # Adjust the length as needed

  heading_style = ParagraphStyle(name='Heading3', parent=styles['Heading3'], alignment=0)  # 0 = Left alignment
  name=billGeneration[0].patientID.patientName
  name2Use=f"<b>Patient name:  {name}</b>"
  heading = Paragraph(name2Use, heading_style)
  elements.append(heading)

  #add Bill Number
  bill = billGeneration[0].billNo
  billD = billGeneration[0].billDate
  billInfo=f"<b>Bill No:</b> {bill}"
  heading= Paragraph(billInfo, heading_style)
  elements.append(heading)
  
  #adding a spacer between bill numbe and bill date
  elements.append(Spacer(20, 0))
  
  #add Bill Date
  billDInfo=f"<b>Bill Date:</b> {billD}"
  heading = Paragraph(billDInfo, heading_style)
  elements.append(heading)
  
  #add Patient phone Number
  PNo= billGeneration[0].patientID.patientPhoneNo
  Phone2Use=f"<b>Phone Number: {PNo}</b>"
  heading = Paragraph(Phone2Use, heading_style)
  elements.append(heading)  


  # Add data table
  table = Table(data)

  # Style the table
  style = TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                      ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                      ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                      ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                      ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                      ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                      ('GRID', (0, 0), (-1, -1), 1, colors.black)])

  table.setStyle(style)
  elements.append(table)

  # Register Hindi font
  #pdfmetrics.registerFont(TTFont('HindiFont', 'Hind-Regular.ttf'))

  # Use the Hindi font in your style
  #heading_style.fontName = 'HindiFont'
  #hindiText="""(कट स्ट्रिप को वापस नहीं किया जा सकता है)"""
  #footnote_para=Paragraph(hindiText,heading_style)
  #elements.append(footnote_para)
  
  heading_style = ParagraphStyle(name='Heading3', parent=styles['Heading3'], alignment=2)
  sig=f"(Auth. Signature)"
  heading=Paragraph(sig, heading_style)
  elements.append(heading)
  
  # Build PDF
  doc.build(elements)
  output.close()

  #temp_pdf_path = "temp.pdf"
  #merge_to_bil_path = "bills.pdf"
  #merge_pdf(temp_pdf_path, merge_to_bil_path)
  
  # pharmacyapp/views/misc_views.py
  
def welcome(request):
  """Render a simple popup or welcome screen."""
  return render(request, 'pharmacyapp/popup.html')

def today_date():
  """Utility function to return today's date."""
  return timezone.now().date()

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