from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.models import User
from .forms import UserCreateForm, UserUpdateForm, ChangePasswordForm, AdminChangePasswordForm, ResetPasswordForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator

def user_login(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'login':
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('user_list')
            else:
                login_url = reverse('login')
                redirect_url = f"{login_url}?error=1"
                return HttpResponseRedirect(redirect_url)
        elif form_type == 'forgot_password':
            form = ResetPasswordForm(request.POST)
            if form.is_valid():
                username = form.cleaned_data['username']
                try:
                    user = User.objects.get(username=username)
                    token_generator = PasswordResetTokenGenerator()
                    token = token_generator.make_token(user)
                    uid = urlsafe_base64_encode(force_bytes(user.pk))
                    reset_url = request.build_absolute_uri(
                        reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
                    )
                    subject = "Password Reset Requested"
                    message = render_to_string('login_password_reset_email.html', {
                        'user': user,
                        'reset_url': reset_url,
                    })
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
                    messages.success(request, "Password reset instructions have been sent to the email address associated with the account.")
                    return redirect('login')
                except User.DoesNotExist:
                    messages.error(request, "No user found with this username.")
                    return redirect('login')
            else:
                messages.error(request, "Invalid input for password reset.")
                return redirect('login')
    return render(request, 'login.html')

def admin_required(view_func):
    decorated_view_func = user_passes_test(lambda u: u.is_superuser)(view_func)
    return decorated_view_func

@login_required(login_url='login')
@admin_required
def admin_change_password(request, user_id):
    user_to_change = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        form = AdminChangePasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data.get('new_password')
            user_to_change.set_password(new_password)
            user_to_change.save()
            messages.success(request, f"Password for user {user_to_change.username} has been changed.")
            return redirect('user_list')
    else:
        form = AdminChangePasswordForm()
    return render(request, 'admin_change_password.html', {'form': form, 'user_to_change': user_to_change})

@login_required(login_url='login')
def change_password(request):
    if request.method == 'POST':
        if 'confirm' in request.POST:
            form = ChangePasswordForm(request.session.get('change_password_form_data'))
            if form.is_valid():
                new_password = form.cleaned_data.get('new_password')
                user = request.user
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)  # Important to keep the user logged in
                if 'change_password_form_data' in request.session:
                    del request.session['change_password_form_data']
                messages.success(request, "Password changed successfully.")
                return redirect('change_password_success')
            else:
                # Form data invalid, redirect back to change password form
                return redirect('change_password')
        elif 'cancel' in request.POST:
            # User cancelled password change
            if 'change_password_form_data' in request.session:
                del request.session['change_password_form_data']
            return redirect('change_password')
        else:
            # Initial form submission
            form = ChangePasswordForm(request.POST)
            if form.is_valid():
                old_password = form.cleaned_data.get('old_password')
                user = request.user
                if not user.check_password(old_password):
                    form.add_error('old_password', 'Old password is incorrect.')
                    return render(request, 'change_password.html', {'form': form})
                # Save form data in session and show confirmation page
                request.session['change_password_form_data'] = request.POST
                return render(request, 'change_password_confirm.html', {'form': form})
            else:
                return render(request, 'change_password.html', {'form': form})
    else:
        form = ChangePasswordForm()
    return render(request, 'change_password.html', {'form': form})

@login_required(login_url='login')
def change_password_success(request):
    return render(request, 'change_password_success.html')

def user_logout(request):
    logout(request)
    return redirect('login')

@login_required(login_url='login')
def user_list(request):
    search_query = request.GET.get('search', '')
    users = User.objects.all().order_by('id')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        users_data = []
        for user in page_obj:
            gender_name = ''
            address = ''
            date_of_birth = ''
            if hasattr(user, 'profile'):
                if user.profile.gender:
                    gender_name = user.profile.gender.name
                address = user.profile.address or ''
                date_of_birth = user.profile.date_of_birth or ''
            users_data.append({
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'gender': gender_name,
                'address': address,
                'date_of_birth': date_of_birth,
            })
        data = {
            'users': users_data,
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
            'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
            'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
            'current_page': page_obj.number,
            'num_pages': paginator.num_pages,
        }
        return JsonResponse(data)

    return render(request, 'user_list.html', {'page_obj': page_obj, 'search_query': search_query})

@login_required(login_url='login')
def user_add(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            gender = form.cleaned_data.get('gender')
            address = form.cleaned_data.get('address')
            date_of_birth = form.cleaned_data.get('date_of_birth')
            phone_number = form.cleaned_data.get('phone_number')
            if gender:
                user.profile.gender = gender
            if address:
                user.profile.address = address
            if date_of_birth:
                user.profile.date_of_birth = date_of_birth
            if phone_number is not None:
                user.profile.phone_number = phone_number
            user.profile.save()
            messages.success(request, "User added successfully.")
            return redirect('user_list')
    else:
        form = UserCreateForm()
    return render(request, 'user_form.html', {'form': form, 'title': 'Add User'})

@login_required(login_url='login')
def user_edit(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user, user_id=user_id)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            if password:
                user.set_password(password)
            user.save()
            gender = form.cleaned_data.get('gender')
            address = form.cleaned_data.get('address')
            date_of_birth = form.cleaned_data.get('date_of_birth')
            phone_number = form.cleaned_data.get('phone_number')
            if gender:
                user.profile.gender = gender
            else:
                user.profile.gender = None
            user.profile.address = address
            user.profile.date_of_birth = date_of_birth
            if phone_number is not None:
                user.profile.phone_number = phone_number
            user.profile.save()
            messages.success(request, "User updated successfully.")
            return redirect('user_list')
    else:
        initial = {}
        if hasattr(user, 'profile'):
            if user.profile.gender:
                initial['gender'] = user.profile.gender
            initial['address'] = user.profile.address
            initial['date_of_birth'] = user.profile.date_of_birth
            initial['phone_number'] = user.profile.phone_number
        form = UserUpdateForm(instance=user, user_id=user_id, initial=initial)
    return render(request, 'user_form.html', {'form': form, 'title': 'Edit User'})

@login_required(login_url='login')
def user_delete(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        user.delete()
        messages.success(request, "User deleted successfully.")
        return redirect('user_list')
    return render(request, 'user_confirm_delete.html', {'user': user})

from .models import Gender
from .forms import GenderForm

@login_required(login_url='login')
def gender_list(request):
    genders = Gender.objects.all().order_by('id')
    return render(request, 'gender_list.html', {'genders': genders})

@login_required(login_url='login')
def gender_add(request):
    if request.method == 'POST':
        form = GenderForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Gender added successfully.")
            return redirect('gender_list')
    else:
        form = GenderForm()
    return render(request, 'gender_form.html', {'form': form, 'title': 'Add Gender'})

@login_required(login_url='login')
def gender_edit(request, gender_id):
    gender = get_object_or_404(Gender, pk=gender_id)
    if request.method == 'POST':
        form = GenderForm(request.POST, instance=gender)
        if form.is_valid():
            form.save()
            return redirect('gender_list')
    else:
        form = GenderForm(instance=gender)
    return render(request, 'gender_form.html', {'form': form, 'title': 'Edit Gender'})

@login_required(login_url='login')
def gender_delete(request, gender_id):
    gender = get_object_or_404(Gender, pk=gender_id)
    if request.method == 'POST':
        gender.delete()
        messages.success(request, "Gender deleted successfully.")
        return redirect('gender_list')
    return render(request, 'gender_confirm_delete.html', {'gender': gender})

@login_required(login_url='login')
def user_profile_edit(request):
    user = request.user
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user, user_id=user.id)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            if password:
                user.set_password(password)
            user.save()
            gender = form.cleaned_data.get('gender')
            address = form.cleaned_data.get('address')
            date_of_birth = form.cleaned_data.get('date_of_birth')
            if gender:
                user.profile.gender = gender
            else:
                user.profile.gender = None
            user.profile.address = address
            user.profile.date_of_birth = date_of_birth
            user.profile.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('user_list')
    else:
        initial = {}
        if hasattr(user, 'profile'):
            if user.profile.gender:
                initial['gender'] = user.profile.gender
            initial['address'] = user.profile.address
            initial['date_of_birth'] = user.profile.date_of_birth
        form = UserUpdateForm(instance=user, user_id=user.id, initial=initial)
    return render(request, 'user_form.html', {'form': form, 'title': 'Edit Profile'})
