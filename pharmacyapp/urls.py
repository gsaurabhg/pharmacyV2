from django.urls import path
from pharmacyapp.views import (
    inventory_views,
    patient_views,
    procurement_views,
    billing_views,
    reports_views,
    utilities
)

urlpatterns = [
    # Welcome / Home
    path('', utilities.welcome, name='welcome'),

    # Inventory Management
    path('list/', inventory_views.inventory_list, name='inventory_list'),
    path('med_detail/<int:pk>/', inventory_views.med_detail, name='med_detail'),
    path('med/<int:pk>/<str:active_tab>/', inventory_views.med_delete, name='med_delete'),
    path('get-pack-size/', inventory_views.get_pack_size, name='get_pack_size'),
    path('medicineName/details/<int:pk>/remove/', inventory_views.medicine_remove, name='medicine_remove'),
    path('bill/details/<int:pk>/', inventory_views.meds_edit, name='meds_edit'),
    path('medicineName/<str:medName>/get_batch_no/', inventory_views.get_batch_no, name='get_batch_no'),
    path('batchNo/<str:batchNo>/get_quantity/', inventory_views.get_quantity, name='get_quantity'),

    # Procurement
    path('procurement/form/', procurement_views.procurement_form, name='procurement_form'),

    # Unified Patient Dashboard
    path('patient/dashboard/', patient_views.patient_dashboard, name='patient_dashboard'),
    path('queue/view-only/', patient_views.queue_view_only, name='queue_view_only'),
    path('patient/register-from-search/', patient_views.register_patient_from_search, name='register_patient_from_search'),
    
    # Billing (per patient)
    path('patient/<int:pk>/bill/', billing_views.bill_details, name='bill_details'),
    path('patient/<int:pk>/order/', billing_views.medicine_order, name='medicine_order'),
    path('patient/<int:pk>/checkout/', billing_views.medicine_checkout, name='medicine_checkout'),
    path('patient/<int:pk>/previouscheckout/', billing_views.medicine_last_checkout, name='medicine_last_checkout'),
    path('final-bill/<str:bill_no>/', billing_views.final_bill_view, name='final_bill_view'),
    path("return-meds/", billing_views.return_meds_redirect, name="return_meds_redirect"),
    path("meds-return/<int:pk>/", billing_views.meds_return_view, name="meds_return"),

    # Reports
    path('post/report/sales/', reports_views.report_sales, name='report_sales'),
    path('post/report/returns/', reports_views.report_returns, name='report_returns'),
    path('post/report/purchases/', reports_views.report_purchases, name='report_purchases'),

    # Utilities
    path('dump-database/', utilities.dump_database_view, name='dump_database'),
    path('send-email/', utilities.send_email_view, name='send_email'),
    path('load-data/', utilities.load_data_view, name='load_data'),

    # Queue Management (now tied to dashboard, but URLs still used by forms/buttons)
    path('queue/add/', patient_views.add_patient_to_queue, name='add_patient_to_queue'),
    path('queue/serve/<int:entry_id>/', patient_views.serve_patient, name='serve_patient'),
    path('queue/clear-served/', patient_views.clear_served_patients, name='clear_served_patients'),
    path('swap-queue/<int:entry_id>/', patient_views.swap_patient_queue, name='swap_patient_queue'),

    # Optional legacy (if not using anymore, safe to remove)
    #path('patient/details/', billing_views.patient_details, name='patient_details'),
    # path('queue/', patient_views.patient_queue, name='patient_queue'),  # Legacy
]
