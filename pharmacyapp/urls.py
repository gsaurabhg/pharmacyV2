from django.urls import re_path as url
from django.urls import path
from . import views


urlpatterns = [
    url(r'^$', views.welcome, name='welcome'),
    url(r'^list$', views.inventory_list, name='inventory_list'),
    url(r'^med_detail/(?P<pk>\d+)/$', views.med_detail, name='med_detail'),
    url(r'^procurement/form/$', views.procurement_form, name='procurement_form'),
    path('get-pack-size/', views.get_pack_size, name='get_pack_size'),
    path('med/<int:pk>/<str:active_tab>/', views.med_delete, name='med_delete'),
    url(r'^post/report/sales/$', views.report_sales, name='report_sales'),
    url(r'^post/report/returns/$', views.report_purchases, name='report_purchases'),
    url(r'^post/report/returns/$', views.report_returns, name='report_returns'),
    url(r'^patient/details/$', views.patient_details, name='patient_details'),
    url(r'^Patient/details/(?P<pk>\d+)/$', views.bill_details, name='bill_details'),
    url(r'^Patient/details/(?P<pk>\d+)/order/$', views.medicine_order, name='medicine_order'),
    url(r'^Patient/details/(?P<pk>\d+)/checkout/$', views.medicine_checkout, name='medicine_checkout'),
    path('final-bill/<str:bill_no>/', views.final_bill_view, name='final_bill_view'),
    url(r'^Patient/details/(?P<pk>\d+)/Previouscheckout/$', views.medicine_last_checkout, name='medicine_last_checkout'),
    url(r'^medicineName/details/(?P<pk>\d+)/remove/$', views.medicine_remove, name='medicine_remove'),
    url(r'^medicineName/(?P<medName>[-\w]+)/get_batch_no/$', views.get_batch_no,name='get_batch_no'),
    url(r'^medicineName/(?P<medName>[^"]*)/get_batch_no/$', views.get_batch_no,name='get_batch_no'),
    url(r'^bill/details/(?P<pk>\d+)/$', views.meds_edit, name='meds_edit'),
    url(r'^batchNo/(?P<batchNo>[^"]*)/get_quantity/$', views.get_quantity,name='get_quantity'),
    path('dump-database/', views.dump_database_view, name='dump_database'),
    path('send-email/', views.send_email_view, name='send_email'),
    path('load-data/', views.load_data_view, name='load_data'),
]
