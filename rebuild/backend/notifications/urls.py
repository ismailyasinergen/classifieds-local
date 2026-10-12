from django.urls import path
from . import views

app_name = "notifications"
urlpatterns = [
    path('<int:search_id>/bildirim-ac/', views.preference, {'enabled': True}, name='enable'),
    path('<int:search_id>/bildirim-durdur/', views.preference, {'enabled': False}, name='disable'),
    path('bildirimler/', views.inbox, name='inbox'),
    path('bildirimler/<int:delivery_id>/okundu/', views.mark, name='read'),
    path('bildirimler/<int:delivery_id>/arsiv/', views.mark, {'archive': True}, name='archive'),
    path("", views.index, name="index"),
    path("kaydet/", views.save, name="save"),
    path("<int:search_id>/ac/", views.open_search, name="open"),
    path("<int:search_id>/ad/", views.rename, name="rename"),
    path("<int:search_id>/sil/", views.delete, name="delete"),
]
