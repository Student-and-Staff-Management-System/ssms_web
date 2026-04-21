import os

code_to_append = """
from staffs.models import ConferenceParticipation, JournalPublication, BookPublication, StaffSeminar, StaffAwardHonour

def scholar_portfolio(request):
    roll_number = request.session.get('student_roll_number')
    if not roll_number: return redirect('scholar_login')
    
    student = get_object_or_404(Student, roll_number=roll_number, program_level='PHD')
    
    conferences = student.scholar_conferences.all().order_by('-year_of_publication', '-created_at')
    journals = student.scholar_journals.all().order_by('-published_year', '-created_at')
    books = student.scholar_books.all().order_by('-year_of_publication', '-created_at')
    seminars = student.scholar_seminars.all().order_by('-year', '-order')
    awards = student.scholar_awards.all().order_by('-year', '-order')
    
    return render(request, 'scholars/scholar_portfolio.html', {
        'student': student,
        'conferences': conferences,
        'journals': journals,
        'books': books,
        'seminars': seminars,
        'awards': awards,
    })

def scholar_portfolio_add(request, form_type):
    roll_number = request.session.get('student_roll_number')
    if not roll_number: return redirect('scholar_login')
    
    student = get_object_or_404(Student, roll_number=roll_number, program_level='PHD')
    staff_list = Staff.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        staff_id = request.POST.get('staff_id')
        staff = get_object_or_404(Staff, staff_id=staff_id) if staff_id else None
        
        if not staff:
            messages.error(request, "Please select a Staff member.")
            return redirect(request.path)
            
        if form_type == 'conference':
            item = ConferenceParticipation(student=student, staff=staff)
            item.participation_type = request.POST.get('participation_type', 'Presented')
            item.national_international = request.POST.get('national_international', 'National')
            item.author_name = request.POST.get('author_name', '').strip()
            item.year_of_publication = request.POST.get('year_of_publication', '').strip()
            item.title_of_paper = request.POST.get('title_of_paper', '').strip()
            item.title_of_proceedings = request.POST.get('title_of_proceedings', '').strip()
            item.date_from = request.POST.get('date_from') or None
            item.date_to = request.POST.get('date_to') or None
            item.location = request.POST.get('location', '').strip()
            item.page_numbers_from = request.POST.get('page_numbers_from', '').strip()
            item.page_numbers_to = request.POST.get('page_numbers_to', '').strip()
            item.place_of_publication = request.POST.get('place_of_publication', '').strip()
            item.publisher_proceedings = request.POST.get('publisher_proceedings', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            messages.success(request, "Conference added.")
        
        elif form_type == 'journal':
            item = JournalPublication(student=student, staff=staff)
            item.national_international = request.POST.get('national_international', 'National')
            item.published_month = request.POST.get('published_month', '').strip()
            item.published_year = request.POST.get('published_year', '').strip()
            item.author_name = request.POST.get('author_name', '').strip()
            item.title_of_paper = request.POST.get('title_of_paper', '').strip()
            item.journal_name = request.POST.get('journal_name', '').strip()
            item.volume_number = request.POST.get('volume_number', '').strip()
            item.issue_number = request.POST.get('issue_number', '').strip()
            item.year_of_publication_doi = request.POST.get('year_of_publication_doi', '').strip()
            item.page_numbers_from = request.POST.get('page_numbers_from', '').strip()
            item.page_numbers_to = request.POST.get('page_numbers_to', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            messages.success(request, "Journal added.")
            
        elif form_type == 'book':
            item = BookPublication(student=student, staff=staff)
            item.type = request.POST.get('type', 'Book')
            item.author_name = request.POST.get('author_name', '').strip()
            item.title_of_book = request.POST.get('title_of_book', '').strip()
            item.publisher_name = request.POST.get('publisher_name', '').strip()
            item.publisher_address = request.POST.get('publisher_address', '').strip()
            item.isbn_issn_number = request.POST.get('isbn_issn_number', '').strip()
            item.page_numbers_from = request.POST.get('page_numbers_from', '').strip()
            item.page_numbers_to = request.POST.get('page_numbers_to', '').strip()
            item.month_of_publication = request.POST.get('month_of_publication', '').strip()
            item.year_of_publication = request.POST.get('year_of_publication', '').strip()
            item.url_address = request.POST.get('url_address', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            messages.success(request, "Book added.")
            
        elif form_type == 'seminar':
            item = StaffSeminar(student=student, staff=staff)
            item.title = request.POST.get('title', '').strip()
            item.event_type = request.POST.get('event_type', 'Seminar')
            item.venue_or_description = request.POST.get('venue_or_description', '').strip()
            item.date_from = request.POST.get('date_from') or None
            item.date_to = request.POST.get('date_to') or None
            item.year = request.POST.get('year', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            messages.success(request, "Seminar added.")
            
        elif form_type == 'award':
            item = StaffAwardHonour(student=student, staff=staff)
            item.title = request.POST.get('title', '').strip()
            item.category = request.POST.get('category', 'Award')
            item.awarded_by = request.POST.get('awarded_by', '').strip()
            item.year = request.POST.get('year', '').strip()
            item.description = request.POST.get('description', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            messages.success(request, "Award added.")
            
        return redirect('scholar_portfolio')
            
    title_map = {
        'conference': 'Add Conference',
        'journal': 'Add Journal',
        'book': 'Add Book',
        'seminar': 'Add Seminar',
        'award': 'Add Award',
    }
    
    return render(request, 'scholars/scholar_portfolio_form.html', {
        'student': student,
        'staff_list': staff_list,
        'form_type': form_type,
        'title': title_map.get(form_type, 'Add Item'),
    })

def scholar_portfolio_edit(request, form_type, pk):
    roll_number = request.session.get('student_roll_number')
    if not roll_number: return redirect('scholar_login')
    
    student = get_object_or_404(Student, roll_number=roll_number, program_level='PHD')
    staff_list = Staff.objects.filter(is_active=True).order_by('name')
    
    model_map = {
        'conference': ConferenceParticipation,
        'journal': JournalPublication,
        'book': BookPublication,
        'seminar': StaffSeminar,
        'award': StaffAwardHonour,
    }
    ModelClass = model_map.get(form_type)
    if not ModelClass: return redirect('scholar_portfolio')
    
    item = get_object_or_404(ModelClass, pk=pk, student=student)
    
    if request.method == 'POST':
        staff_id = request.POST.get('staff_id')
        staff = get_object_or_404(Staff, staff_id=staff_id) if staff_id else None
        
        if staff:
            item.staff = staff
            
        if form_type == 'conference':
            item.participation_type = request.POST.get('participation_type', 'Presented')
            item.national_international = request.POST.get('national_international', 'National')
            item.author_name = request.POST.get('author_name', '').strip()
            item.year_of_publication = request.POST.get('year_of_publication', '').strip()
            item.title_of_paper = request.POST.get('title_of_paper', '').strip()
            item.title_of_proceedings = request.POST.get('title_of_proceedings', '').strip()
            item.date_from = request.POST.get('date_from') or None
            item.date_to = request.POST.get('date_to') or None
            item.location = request.POST.get('location', '').strip()
            item.page_numbers_from = request.POST.get('page_numbers_from', '').strip()
            item.page_numbers_to = request.POST.get('page_numbers_to', '').strip()
            item.place_of_publication = request.POST.get('place_of_publication', '').strip()
            item.publisher_proceedings = request.POST.get('publisher_proceedings', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            messages.success(request, "Conference updated.")
        
        elif form_type == 'journal':
            item.national_international = request.POST.get('national_international', 'National')
            item.published_month = request.POST.get('published_month', '').strip()
            item.published_year = request.POST.get('published_year', '').strip()
            item.author_name = request.POST.get('author_name', '').strip()
            item.title_of_paper = request.POST.get('title_of_paper', '').strip()
            item.journal_name = request.POST.get('journal_name', '').strip()
            item.volume_number = request.POST.get('volume_number', '').strip()
            item.issue_number = request.POST.get('issue_number', '').strip()
            item.year_of_publication_doi = request.POST.get('year_of_publication_doi', '').strip()
            item.page_numbers_from = request.POST.get('page_numbers_from', '').strip()
            item.page_numbers_to = request.POST.get('page_numbers_to', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            messages.success(request, "Journal updated.")
            
        elif form_type == 'book':
            item.type = request.POST.get('type', 'Book')
            item.author_name = request.POST.get('author_name', '').strip()
            item.title_of_book = request.POST.get('title_of_book', '').strip()
            item.publisher_name = request.POST.get('publisher_name', '').strip()
            item.publisher_address = request.POST.get('publisher_address', '').strip()
            item.isbn_issn_number = request.POST.get('isbn_issn_number', '').strip()
            item.page_numbers_from = request.POST.get('page_numbers_from', '').strip()
            item.page_numbers_to = request.POST.get('page_numbers_to', '').strip()
            item.month_of_publication = request.POST.get('month_of_publication', '').strip()
            item.year_of_publication = request.POST.get('year_of_publication', '').strip()
            item.url_address = request.POST.get('url_address', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            messages.success(request, "Book updated.")
            
        elif form_type == 'seminar':
            item.title = request.POST.get('title', '').strip()
            item.event_type = request.POST.get('event_type', 'Seminar')
            item.venue_or_description = request.POST.get('venue_or_description', '').strip()
            item.date_from = request.POST.get('date_from') or None
            item.date_to = request.POST.get('date_to') or None
            item.year = request.POST.get('year', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            messages.success(request, "Seminar updated.")
            
        elif form_type == 'award':
            item.title = request.POST.get('title', '').strip()
            item.category = request.POST.get('category', 'Award')
            item.awarded_by = request.POST.get('awarded_by', '').strip()
            item.year = request.POST.get('year', '').strip()
            item.description = request.POST.get('description', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            messages.success(request, "Award updated.")
            
        return redirect('scholar_portfolio')
            
    title_map = {
        'conference': 'Edit Conference',
        'journal': 'Edit Journal',
        'book': 'Edit Book',
        'seminar': 'Edit Seminar',
        'award': 'Edit Award',
    }
    
    return render(request, 'scholars/scholar_portfolio_form.html', {
        'student': student,
        'staff_list': staff_list,
        'form_type': form_type,
        'item': item,
        'title': title_map.get(form_type, 'Edit Item'),
    })

def scholar_portfolio_delete(request, form_type, pk):
    roll_number = request.session.get('student_roll_number')
    if not roll_number: return redirect('scholar_login')
    
    student = get_object_or_404(Student, roll_number=roll_number, program_level='PHD')
    
    model_map = {
        'conference': ConferenceParticipation,
        'journal': JournalPublication,
        'book': BookPublication,
        'seminar': StaffSeminar,
        'award': StaffAwardHonour,
    }
    ModelClass = model_map.get(form_type)
    if ModelClass:
        get_object_or_404(ModelClass, pk=pk, student=student).delete()
        messages.success(request, "Entry deleted.")
        
    return redirect('scholar_portfolio')

"""

file_path = "c:\\Users\\sachi\\OneDrive\\Desktop\\nojinx\\ssm\\students\\scholars_views.py"

with open(file_path, "a") as f:
    f.write(code_to_append)
