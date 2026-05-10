from django.urls import path
from . import admin_views

app_name = 'custom_admin'

urlpatterns = [
    path('', admin_views.dashboard, name='dashboard'),
    path('products/', admin_views.product_list, name='product_list'),
    path('products/add/<str:item_type>/', admin_views.product_upsert, name='product_add'),
    path('products/edit/<str:item_type>/<int:item_id>/', admin_views.product_upsert, name='product_edit'),
    path('products/delete/<str:item_type>/<int:item_id>/', admin_views.product_delete, name='product_delete'),
    
    path('orders/', admin_views.order_list, name='order_list'),
    path('orders/<int:order_id>/', admin_views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/invoice/', admin_views.order_invoice, name='order_invoice'),
    path('orders/<int:order_id>/status/', admin_views.order_status_update, name='order_status_update'),
    
    path('inventory/', admin_views.inventory_manage, name='inventory_manage'),
    path('inventory/export/', admin_views.inventory_export_csv, name='inventory_export'),
    path('coupons/', admin_views.coupon_list, name='coupon_list'),
    path('coupons/add/', admin_views.coupon_upsert, name='coupon_add'),
    path('coupons/edit/<int:coupon_id>/', admin_views.coupon_upsert, name='coupon_edit'),
    path('coupons/delete/<int:coupon_id>/', admin_views.coupon_delete, name='coupon_delete'),
    
    path('reviews/', admin_views.feedback_manage, name='feedback_manage'),
    path('reviews/messages/<int:message_id>/toggle-read/', admin_views.contact_message_toggle_read, name='contact_message_toggle_read'),
    path('reviews/product/<int:review_id>/delete/', admin_views.product_review_delete, name='product_review_delete'),
    path('settings/', admin_views.settings_manage, name='settings_manage'),
    path('settings/reorder-banners/', admin_views.update_banner_order, name='reorder_banners'),
]
