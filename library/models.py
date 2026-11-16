from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=150)
    year = models.IntegerField()
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "year": self.year,
            "available": self.available,
            "created_at": self.created_at.isoformat(),
        }
    

class Loan(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="loans")
    person_name = models.CharField(max_length=150)
    loan_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)

    def to_dict(self):
        return {
            "id": self.id,
            "book": self.book.to_dict(),
            "person_name": self.person_name,
            "loan_date": self.loan_date.isoformat(),
            "return_date": self.return_date.isoformat() if self.return_date else None,
        }