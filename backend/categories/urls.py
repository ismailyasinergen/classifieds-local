from django.urls import path

from .views import CategoryListingListView

app_name = "categories"

urlpatterns = [
    path("categories/<slug:slug>/", CategoryListingListView.as_view(), name="category_detail"),
]
