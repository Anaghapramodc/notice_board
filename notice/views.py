from django.shortcuts import render, redirect, get_object_or_404
from .models import Notice
from .form import NoticeForm, StudentRegisterForm, HodRegisterForm, StaffRegisterForm, EmailLoginForm, ProfileUpdateForm
# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
User = get_user_model()
from webpush import send_user_notification

def home(request):
    latest_events = Notice.objects.filter(
        display_category='events'
    ).order_by('-created_at')[:6]

    return render(request, 'home.html', {
        'latest_events': latest_events
    })

def about(request):
    return render(request, 'about.html')

# CREATE NOTICE
from django.contrib.auth.decorators import login_required

@login_required
def create_notice(request):

    if request.user.user_type not in ['hod', 'staff']:
        return redirect('notice_list')

    if request.method == 'POST':
        form = NoticeForm(request.POST, request.FILES)
        if form.is_valid():
            notice = form.save(commit=False)
            notice.created_by = request.user

            # STAFF → Office notice (ALL users)
            if request.user.user_type == 'staff':
                notice.category = 'office'
                notice.department = None

            # HOD → Department notice
            elif request.user.user_type == 'hod':
                notice.category = 'department'
                notice.department = request.user.department

            notice.save()

            # ================= EMAIL LOGIC =================

            # 🔥 SUBJECT LOGIC
            if notice.display_category == 'urgent':
                subject = f"🛑 URGENT NOTIFICATION HAS ARRIVED 🛑 - {notice.notice_subject}"
            else:
                subject = f"New Notice: {notice.notice_subject}"

            message = f"""
            {notice.notice_subject}

            {notice.message}

            Please login to portal for full details.
            """

            recipient_list = []

            # HOD → Only students of that department
            if request.user.user_type == 'hod':
                students = User.objects.filter(
                    user_type='student',
                    department=request.user.department
                )
                recipient_list = [s.email for s in students]

            # STAFF → ALL students + HODs
            elif request.user.user_type == 'staff':
                users = User.objects.filter(user_type__in=['student', 'hod'])
                recipient_list = [u.email for u in users]

            if recipient_list:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    recipient_list,
                    fail_silently=False,
                )

            # =================================================

            # ================= BROWSER PUSH NOTIFICATION =================

            payload = {
                "head": "New Notice Published",
                "body": notice.notice_subject,
            }

            # HOD → students in department
            if request.user.user_type == 'hod':
                students = User.objects.filter(
                    user_type='student',
                    department=request.user.department
                )

                for student in students:
                    send_user_notification(user=student, payload=payload, ttl=1000)

            # STAFF → all students + all HODs
            elif request.user.user_type == 'staff':
                users = User.objects.filter(user_type__in=['student', 'hod'])

                for user in users:
                    send_user_notification(user=user, payload=payload, ttl=1000)

            return redirect('notice_list')


    else:
        form = NoticeForm()

    return render(request, 'create_notice.html', {'form': form})


@login_required
def notice_categories(request):

    user = request.user

    # Role-based filtering (same logic as notice_list)
    if user.user_type == 'student':
        notices = Notice.objects.filter(
            Q(category='office') |
            Q(category='department', department=user.department)
        )

    elif user.user_type == 'hod':
        notices = Notice.objects.filter(
            Q(category='office') |
            Q(category='department', department=user.department)
        )

    elif user.user_type == 'staff':
        notices = Notice.objects.filter(category='office')

    else:
        notices = Notice.objects.none()

    # 🔥 CHECK IF ANY URGENT NOTICE EXISTS
    urgent_exists = notices.filter(display_category='urgent').exists()

    return render(request, 'notice_categories.html', {
        'urgent_exists': urgent_exists
    })
@login_required
def notice_by_category(request, cat):

    user = request.user

    # ================= BASE FILTER =================

    if user.user_type == 'student':
        base_notices = Notice.objects.filter(
            Q(category='office') |
            Q(category='department', department=user.department)
        )

    elif user.user_type == 'hod':
        base_notices = Notice.objects.filter(
            Q(category='office') |
            Q(category='department', department=user.department)
        )

    elif user.user_type == 'staff':
        base_notices = Notice.objects.filter(category='office')

    else:
        base_notices = Notice.objects.none()

    # ================= CATEGORY FILTER =================

    if cat == "all":
        notices = base_notices

    elif cat == "department_updates":
        # 🔥 ONLY department notices for their department
        notices = Notice.objects.filter(
            category='department',
            department=user.department
        )

    else:
        notices = base_notices.filter(display_category=cat)

    return render(request, 'notice_list.html', {
        'notices': notices.order_by('-created_at'),
        'selected_category': cat
    })


@login_required
def notice_list(request):

    user = request.user

    if user.user_type == 'student':
        notices = Notice.objects.filter(
            Q(category='office') |
            Q(category='department', department=user.department)
        )

        # HOD → office + own department  ✅ FIXED
    elif user.user_type == 'hod':
        notices = Notice.objects.filter(
            Q(category='office') |
            Q(category='department', department=user.department)
        )

    elif user.user_type == 'staff':
        notices = Notice.objects.filter(category='office')

    else:
        notices = Notice.objects.none()

    return render(request, 'notice_list.html', {'notices': notices.order_by('-created_at')})


# VIEW SINGLE NOTICE
def notice_detail(request, pk):
    notice = get_object_or_404(Notice, pk=pk)
    return render(request, 'notice_detail.html', {'notice': notice})

# DELETE NOTICE
def delete_notice(request, pk):
    notice = get_object_or_404(Notice, pk=pk)
    notice.delete()
    return redirect('notice_list')

def choose_category(request):
    return render(request, 'choose_category.html')

def register_student(request):
    if request.method == 'POST':
        form = StudentRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = StudentRegisterForm()
    return render(request, 'register.html', {'form': form, 'title': 'Student Registration'})

def register_hod(request):
    if request.method == 'POST':
        form = HodRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = HodRegisterForm()
    return render(request, 'register.html', {'form': form, 'title': 'HOD Registration'})

def register_staff(request):
    if request.method == 'POST':
        form = StaffRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = StaffRegisterForm()
    return render(request, 'register.html', {'form': form, 'title': 'Office Staff Registration'})

def user_login(request):
    if request.method == 'POST':
        form = EmailLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_active:
                form.add_error(None, "Your account is not approved by admin yet.")
            else:
                login(request, user)
                return redirect('profile')
    else:
        form = EmailLoginForm()
    return render(request, 'login.html', {'form': form})

from .form import ProfileUpdateForm

@login_required
def profile(request):
    user = request.user

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=user)

    return render(request, 'profile.html', {
        'user': user,
        'form': form
    })

def user_logout(request):
    logout(request)
    return redirect('home')


from openai import OpenAI
from django.conf import settings

import openai



from openai import OpenAI
import os

client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

@csrf_exempt
def chatbot(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message", "").lower().strip()

        # ================= RULE BASED ANSWERS =================

        rules = {

            # 🔹 Basic Questions
            "admission fee": "The admission fee for all courses is ₹2000.",
            "affiliation fee": "The affiliation fee is ₹600.",
            "id card fee": "The ID card fee is ₹100.",
            "arts & sports fee": "The Arts & Sports fee is ₹500.",
            "college union": "The College Union Activities & Magazine fee is ₹1000.",
            "caution deposit": "The caution deposit is ₹500 (Refundable).",
            "pta fee": "The PTA fee is ₹1600 (₹1500 for some courses).",

            # 🔹 Course Specific
            "sanctioned strength of b.sc computer science": "The sanctioned strength of B.Sc Computer Science is 35 students.",
            "microbiology tuition fee": "The tuition fee of B.Sc Microbiology is ₹16000 per semester.",
            "biochemistry tuition fee": "The tuition fee of B.Sc Biochemistry is ₹12000 per semester.",
            "nil lab fee": "B.Com Marketing has NIL lab fee.",
            "b.com tuition fee": "The tuition fee of B.Com courses is ₹9000 per semester.",
            "b.a english tuition fee": "The tuition fee of B.A English is ₹11000 per semester.",
            "b.a economics tuition fee": "The tuition fee of B.A Economics is ₹15000 per semester.",

            # 🔹 Admission Time Fees
            "admission time fee for b.sc computer science": "Admission time fee for B.Sc Computer Science is ₹19,200.",
            "admission time fee for b.sc microbiology": "Admission time fee for B.Sc Microbiology is ₹23,200.",
            "admission time fee for b.sc biotechnology": "Admission time fee for B.Sc Biotechnology is ₹20,200.",
            "admission time fee for b.com": "Admission time fee for B.Com courses is ₹15,700.",
            "admission time fee for b.a english": "Admission time fee for B.A English is ₹18,700.",
            "highest admission time fee": "B.Sc Microbiology & B.A Economics have the highest admission time fee – ₹23,200.",

            # 🔹 Semester Fees
            "semester fee of b.sc computer science": "The semester fee of B.Sc Computer Science is ₹11,000.",
            "semester fee of b.sc microbiology": "The semester fee of B.Sc Microbiology is ₹16,000.",
            "semester fee of b.com": "The semester fee of B.Com courses is ₹9,000.",
            "semester fee of b.a economics": "The semester fee of B.A Economics is ₹16,000.",
            "lowest semester fee": "B.Com courses have the lowest semester fee – ₹9,000.",

            # 🔹 Comparison
            "highest tuition fee": "B.Sc Microbiology & B.A Economics have the highest tuition fee – ₹16,000 per semester.",
            "lowest tuition fee": "B.Com courses have the lowest tuition fee – ₹9,000 per semester.",
            "sanctioned strength 26": "Courses with sanctioned strength 26: B.Sc Biochemistry, B.Sc Biotechnology, B.A English, B.A Economics.",
            "sanctioned strength 40": "Courses with sanctioned strength 40: B.Com with Computer Application, B.Com Marketing, B.B.A.",
        }

        # 🔍 Rule Matching
        for key in rules:
            if all(word in user_message for word in key.split()):
                return JsonResponse({"reply": rules[key]})

        # ================= AI FALLBACK =================

        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a helpful college assistant. Answer clearly and shortly."},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7
            )

            reply = completion.choices[0].message.content

        except Exception as e:
            print("AI ERROR:", e)
            reply = "AI server waking up... try again."

        return JsonResponse({"reply": reply})

def all_events(request):
    events = Notice.objects.filter(
        display_category='events'
    ).order_by('-created_at')

    return render(request, 'all_events.html', {
        'events': events
    })


@login_required
def update_notice(request, pk):

    notice = get_object_or_404(Notice, pk=pk)

    # Only creator can edit
    if request.user != notice.created_by:
        return redirect('notice_list')

    if request.method == 'POST':
        form = NoticeForm(request.POST, request.FILES, instance=notice)
        if form.is_valid():
            form.save()
            return redirect('notice_list')
    else:
        form = NoticeForm(instance=notice)

    return render(request, 'create_notice.html', {
        'form': form,
        'is_update': True
    })