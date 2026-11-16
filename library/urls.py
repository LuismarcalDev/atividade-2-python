from django.urls import path
from . import views

urlpatterns = [
    path("books", views.books),
    path("books/available", views.books_available),
    path("books/<int:id>", views.book_detail),
    path("loans", views.loans),
    path("loans/<int:id>", views.loan_detail),
]