import json
from datetime import date

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Book, Loan


def erro(mensagem, status):
    return JsonResponse({"error": mensagem}, status=status)


def ler_json(request):
    try:
        dados = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, erro("JSON inválido.", 400)
    if not isinstance(dados, dict):
        return None, erro("O corpo deve ser um objeto JSON.", 400)
    return dados, None


def validar_livro(dados):
    title = dados.get("title")
    author = dados.get("author")
    year = dados.get("year")
    available = dados.get("available", True)

    if not isinstance(title, str) or not title.strip():
        return None, "O campo 'title' é obrigatório."
    if not isinstance(author, str) or not author.strip():
        return None, "O campo 'author' é obrigatório."
    if not isinstance(year, int) or isinstance(year, bool):
        return None, "O campo 'year' deve ser um número inteiro."
    if not isinstance(available, bool):
        return None, "O campo 'available' deve ser true ou false."

    return {"title": title.strip(), "author": author.strip(),
            "year": year, "available": available}, None


def parse_data(valor, campo, obrigatorio):
    if valor is None:
        if obrigatorio:
            return None, f"O campo '{campo}' é obrigatório."
        return None, None
    try:
        return date.fromisoformat(valor), None
    except (TypeError, ValueError):
        return None, f"O campo '{campo}' deve estar no formato AAAA-MM-DD."


# ---------- LIVROS ----------

@csrf_exempt
def books(request):
    if request.method == "GET":
        lista = [b.to_dict() for b in Book.objects.all()]
        return JsonResponse(lista, safe=False, status=200)

    if request.method == "POST":
        dados, falha = ler_json(request)
        if falha:
            return falha
        campos, msg = validar_livro(dados)
        if msg:
            return erro(msg, 400)
        livro = Book.objects.create(**campos)
        return JsonResponse(livro.to_dict(), status=201)

    return erro("Método não permitido.", 405)


def books_available(request):
    if request.method != "GET":
        return erro("Método não permitido.", 405)
    lista = [b.to_dict() for b in Book.objects.filter(available=True)]
    return JsonResponse(lista, safe=False, status=200)


@csrf_exempt
def book_detail(request, id):
    try:
        livro = Book.objects.get(id=id)
    except Book.DoesNotExist:
        return erro("Livro não encontrado.", 404)

    if request.method == "GET":
        return JsonResponse(livro.to_dict(), status=200)

    if request.method == "PUT":
        dados, falha = ler_json(request)
        if falha:
            return falha
        campos, msg = validar_livro(dados)
        if msg:
            return erro(msg, 400)
        for nome, valor in campos.items():
            setattr(livro, nome, valor)
        livro.save()
        return JsonResponse(livro.to_dict(), status=200)

    if request.method == "DELETE":
        livro.delete()
        return HttpResponse(status=204)

    return erro("Método não permitido.", 405)


# ---------- EMPRÉSTIMOS ----------

@csrf_exempt
def loans(request):
    if request.method == "GET":
        lista = [l.to_dict() for l in Loan.objects.select_related("book")]
        return JsonResponse(lista, safe=False, status=200)

    if request.method == "POST":
        dados, falha = ler_json(request)
        if falha:
            return falha

        book_id = dados.get("book_id")
        person_name = dados.get("person_name")

        if not isinstance(book_id, int) or isinstance(book_id, bool):
            return erro("O campo 'book_id' deve ser um número inteiro.", 400)
        if not isinstance(person_name, str) or not person_name.strip():
            return erro("O campo 'person_name' é obrigatório.", 400)

        loan_date, msg = parse_data(dados.get("loan_date"), "loan_date", True)
        if msg:
            return erro(msg, 400)
        return_date, msg = parse_data(dados.get("return_date"), "return_date", False)
        if msg:
            return erro(msg, 400)

        try:
            livro = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return erro("Livro inexistente.", 404)

        if not livro.available:
            return erro("Livro indisponível para empréstimo.", 400)

        emprestimo = Loan.objects.create(
            book=livro, person_name=person_name.strip(),
            loan_date=loan_date, return_date=return_date,
        )
        livro.available = return_date is not None
        livro.save()
        return JsonResponse(emprestimo.to_dict(), status=201)

    return erro("Método não permitido.", 405)


@csrf_exempt
def loan_detail(request, id):
    try:
        emprestimo = Loan.objects.select_related("book").get(id=id)
    except Loan.DoesNotExist:
        return erro("Empréstimo não encontrado.", 404)

    if request.method == "GET":
        return JsonResponse(emprestimo.to_dict(), status=200)

    if request.method == "PUT":
        dados, falha = ler_json(request)
        if falha:
            return falha

        person_name = dados.get("person_name")
        if not isinstance(person_name, str) or not person_name.strip():
            return erro("O campo 'person_name' é obrigatório.", 400)

        loan_date, msg = parse_data(dados.get("loan_date"), "loan_date", True)
        if msg:
            return erro(msg, 400)
        return_date, msg = parse_data(dados.get("return_date"), "return_date", False)
        if msg:
            return erro(msg, 400)

        livro_antigo = emprestimo.book
        book_id = dados.get("book_id", livro_antigo.id)
        if not isinstance(book_id, int) or isinstance(book_id, bool):
            return erro("O campo 'book_id' deve ser um número inteiro.", 400)
        try:
            livro_novo = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return erro("Livro inexistente.", 404)

        if livro_novo.id != livro_antigo.id:
            if not livro_novo.available:
                return erro("Livro indisponível para empréstimo.", 400)
            livro_antigo.available = True
            livro_antigo.save()

        emprestimo.book = livro_novo
        emprestimo.person_name = person_name.strip()
        emprestimo.loan_date = loan_date
        emprestimo.return_date = return_date
        emprestimo.save()

        livro_novo.available = return_date is not None
        livro_novo.save()
        return JsonResponse(emprestimo.to_dict(), status=200)

    if request.method == "DELETE":
        if emprestimo.return_date is None:
            emprestimo.book.available = True
            emprestimo.book.save()
        emprestimo.delete()
        return HttpResponse(status=204)

    return erro("Método não permitido.", 405)