import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db.models import Q, Sum
from django.utils import timezone
from .form import *
from .models import *
from django.core.mail import send_mail
from django.conf import settings
import csv
from django.http import HttpResponse
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

# Helper function to create notifications
def create_notification(user, notification_type, title, message_text, related_entity_type=None, related_entity_id=None):
    """
    Create a notification for a user.
    notification_type: 'email', 'sms', or 'push'
    """
    try:
        Notifications.objects.create(
            user=user,
            type=notification_type,
            title=title,
            message=message_text,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id
        )
    except Exception as e:
        print(f"Error creating notification: {str(e)}")

    # Send an email to the user for every notification (if user has email)
    try:
        user_email = getattr(user, 'email', None)
        if user_email:
            subject = title or 'Notification'
            message = message_text or ''
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
            # send_mail will use EMAIL_BACKEND from settings; fail silently in production
            send_mail(subject, message, from_email, [user_email], fail_silently=True)
    except Exception as e:
        print(f"Error sending notification email: {e}")

def home(request):
    featured_properties = Properties.objects.filter(status='available')[:6]
    return render(request, 'home.html', {'featured_properties': featured_properties})

def user_register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            user_type = form.cleaned_data.get('user_type')
            if user_type == 'tenant':
                Tenants.objects.create(user=user)
                messages.success(request, 'Tenant account created successfully! Please login.')
            elif user_type == 'owner':
                Owners.objects.create(user=user)
                messages.success(request, 'Owner account created successfully! Please login.')
            
            return redirect('user_login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'auth/register.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            user = Users.objects.get(email=email)
            if user.check_password(password):
                if user.is_active:
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.first_name}!')
                    
                    if user.user_type == 'admin' or user.is_superuser:
                        return redirect('admin_dashboard')
                    elif user.user_type == 'owner':
                        return redirect('owner_dashboard')
                    else:
                        return redirect('tenant_dashboard')
                else:
                    messages.error(request, 'Your account is disabled.')
            else:
                messages.error(request, 'Invalid email or password.')
        except Users.DoesNotExist:
            messages.error(request, 'Invalid email or password.')
    else:
        pass
    
    return render(request, 'auth/login.html')

@login_required
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')

@login_required
def tenant_dashboard(request):
    if request.user.user_type != 'tenant':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    tenant = get_object_or_404(Tenants, user=request.user)
    bookings = Bookings.objects.filter(tenant=tenant).order_by('-created_at')
    payments = Payments.objects.filter(tenant=tenant).order_by('-created_at')
    complaints = ComplaintsRequests.objects.filter(tenant=tenant).order_by('-created_at')

    # Determine if a payment is currently due for each booking.
    # Payment is considered not due if there is a completed payment whose next due date (one month later)
    # is in the future. Otherwise a payment is due.
    import calendar
    from django.utils import timezone

    today = timezone.now().date()
    for b in bookings:
        try:
            # Prefer explicit pending payments created by the system (or by previous flows)
            pending = Payments.objects.filter(booking=b, payment_status='pending').order_by('due_date').first()
            if pending:
                b.next_payment_due = pending.due_date
                # Show Pay button immediately when a pending payment exists (so tenant can pay right after owner confirms)
                b.payment_due = True
            else:
                # Fallback: compute based on last completed payment (if any)
                last_payment = Payments.objects.filter(booking=b, payment_status='completed').order_by('-payment_date').first()
                if not last_payment or not last_payment.payment_date:
                    b.payment_due = False
                    b.next_payment_due = None
                else:
                    lp = last_payment.payment_date
                    # add 1 calendar month
                    month = lp.month + 1
                    year = lp.year + (month - 1) // 12
                    month = (month - 1) % 12 + 1
                    day = min(lp.day, calendar.monthrange(year, month)[1])
                    next_due = lp.replace(year=year, month=month, day=day)
                    b.next_payment_due = next_due
                    b.payment_due = (today >= next_due)
                # Determine if booking is fully paid up to end_date
                try:
                    pending_up_to_end = Payments.objects.filter(booking=b, payment_status='pending', due_date__lte=b.end_date).exists()
                    completed_any = Payments.objects.filter(booking=b, payment_status='completed').exists()
                    b.fully_paid = (not pending_up_to_end) and completed_any
                except Exception:
                    b.fully_paid = False
        except Exception:
            b.payment_due = True
            b.next_payment_due = None

    # convert back to QuerySet-like ordering in context
    # (we already ordered above and then converted to list)

    # Group complaints for easier display in template
    complaints_open = complaints.filter(status='open')
    complaints_in_progress = complaints.filter(status='in-progress')
    complaints_resolved = complaints.filter(status='resolved')
    
    total_paid = payments.filter(payment_status='completed').aggregate(
        total=Sum('amount')
    )['total'] or 0
    try:
        # Show whole-number amount (BDT) to users
        total_paid = int(round(float(total_paid)))
    except Exception:
        total_paid = 0
    
    context = {
        'tenant': tenant,
        'bookings': bookings,
        'payments': payments,
        'complaints': complaints,
        'complaints_open': complaints_open,
        'complaints_in_progress': complaints_in_progress,
        'complaints_resolved': complaints_resolved,
        'total_paid': total_paid,
        'today': today,
    }
    return render(request, 'dashboard/tenant_dashboard.html', context)

@login_required
def owner_dashboard(request):
    if request.user.user_type != 'owner':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    owner = get_object_or_404(Owners, user=request.user)
    properties = Properties.objects.filter(owner=owner)
    all_bookings = Bookings.objects.filter(property__owner=owner).order_by('-created_at')
    payments = Payments.objects.filter(owner=owner).order_by('-created_at')
    
    pending_bookings = all_bookings.filter(booking_status='pending')
    
    total_properties = properties.count()
    active_bookings = all_bookings.filter(booking_status='confirmed').count()
    total_earnings = payments.filter(payment_status='completed').aggregate(
        total=Sum('amount')
    )['total'] or 0
    try:
        total_earnings = int(round(float(total_earnings)))
    except Exception:
        total_earnings = 0
    context = {
        'owner': owner,
        'properties': properties,
        'bookings': all_bookings,
        'pending_bookings': pending_bookings,
        'total_properties': total_properties,
        'active_bookings': active_bookings,
        'total_earnings': total_earnings,
    }
    return render(request, 'dashboard/owner_dashboard.html', context)

@login_required
def admin_dashboard(request):
    if not request.user.is_superuser and request.user.user_type != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    total_users = Users.objects.count()
    total_properties = Properties.objects.count()
    total_bookings = Bookings.objects.count()
    total_payments = Payments.objects.count()
    
    recent_users = Users.objects.order_by('-created_at')[:5]
    recent_bookings = Bookings.objects.order_by('-created_at')[:5]
    recent_properties = Properties.objects.order_by('-created_at')[:5]
    
    context = {
        'total_users': total_users,
        'total_properties': total_properties,
        'total_bookings': total_bookings,
        'total_payments': total_payments,
        'recent_users': recent_users,
        'recent_bookings': recent_bookings,
        'recent_properties': recent_properties,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)

@login_required
def user_profile(request):
    user = request.user
    
    profile_form = UserProfileForm(instance=user)
    tenant_form = None
    owner_form = None
    
    if user.user_type == 'tenant':
        try:
            tenant = Tenants.objects.get(user=user)
            tenant_form = TenantProfileForm(instance=tenant)
        except Tenants.DoesNotExist:
            tenant_form = TenantProfileForm()
    elif user.user_type == 'owner':
        try:
            owner = Owners.objects.get(user=user)
            owner_form = OwnerProfileForm(instance=owner)
        except Owners.DoesNotExist:
            owner_form = OwnerProfileForm()
    
    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, instance=user)
        
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            
            if user.user_type == 'tenant':
                tenant = Tenants.objects.get(user=user)
                tenant_form = TenantProfileForm(request.POST, instance=tenant)
                if tenant_form.is_valid():
                    tenant_form.save()
            elif user.user_type == 'owner':
                owner = Owners.objects.get(user=user)
                owner_form = OwnerProfileForm(request.POST, instance=owner)
                if owner_form.is_valid():
                    owner_form.save()
            
            return redirect('user_profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    
    context = {
        'profile_form': profile_form,
        'tenant_form': tenant_form,
        'owner_form': owner_form,
    }
    
    return render(request, 'auth/profile.html', context)

@login_required
def property_list(request):
    if request.user.user_type != 'owner':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    owner = get_object_or_404(Owners, user=request.user)
    properties = Properties.objects.filter(owner=owner)
    
    return render(request, 'properties/property_list.html', {'properties': properties})

@login_required
def add_property(request):
    if request.user.user_type != 'owner':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    owner = get_object_or_404(Owners, user=request.user)
    
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES)
        if form.is_valid():
            property_obj = form.save(commit=False)
            property_obj.owner = owner
            property_obj.save()
            # Handle uploaded images: main_image and additional_images
            try:
                main_image = request.FILES.get('main_image')
                if main_image:
                    PropertyImages.objects.create(
                        property=property_obj,
                        image_url=main_image,
                        caption='Main image',
                        is_primary=True
                    )

                additional = request.FILES.getlist('additional_images')
                for img in additional:
                    # skip if same as main
                    if main_image and getattr(img, 'name', None) == getattr(main_image, 'name', None):
                        continue
                    PropertyImages.objects.create(
                        property=property_obj,
                        image_url=img,
                        caption='Additional image',
                        is_primary=False
                    )
            except Exception as e:
                # don't block property creation if images fail; log and continue
                print(f"Error saving property images: {e}")

            messages.success(request, 'Property added successfully!')
            # After adding a property, show it on the owner dashboard
            return redirect('owner_dashboard')
    else:
        form = PropertyForm()
    
    return render(request, 'properties/add_property.html', {'form': form})

@login_required
def edit_property(request, property_id):
    if request.user.user_type != 'owner':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    property_obj = get_object_or_404(Properties, pk=property_id, owner__user=request.user)
    
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES, instance=property_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Property updated successfully!')
            return redirect('property_list')
    else:
        form = PropertyForm(instance=property_obj)
    
    return render(request, 'properties/edit_property.html', {'form': form, 'property': property_obj})

@login_required
def delete_property(request, property_id):
    if request.user.user_type != 'owner':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    property_obj = get_object_or_404(Properties, pk=property_id, owner__user=request.user)
    
    if request.method == 'POST':
        property_obj.delete()
        messages.success(request, 'Property deleted successfully!')
        return redirect('property_list')
    
    return render(request, 'properties/delete_property.html', {'property': property_obj})

def property_search(request):
    properties = Properties.objects.filter(status='available')
    form = PropertySearchForm(request.GET or None)
    
    if form.is_valid():
        address = form.cleaned_data.get('address')
        property_type = form.cleaned_data.get('property_type')
        min_rent = form.cleaned_data.get('min_rent')
        max_rent = form.cleaned_data.get('max_rent')

        if address:
            properties = properties.filter(
                Q(address__icontains=address) | Q(city__icontains=address) | Q(state__icontains=address)
            )
        if property_type:
            properties = properties.filter(property_type=property_type)
        if min_rent:
            properties = properties.filter(rent_amount__gte=min_rent)
        if max_rent:
            properties = properties.filter(rent_amount__lte=max_rent)
    
    context = {
        'properties': properties,
        'form': form,
    }
    return render(request, 'properties/property_search.html', context)

def property_detail(request, property_id):
    property_obj = get_object_or_404(Properties, pk=property_id)
    images = PropertyImages.objects.filter(property=property_obj)
    reviews = ReviewsRatings.objects.filter(property=property_obj, is_approved=True)
    
    context = {
        'property': property_obj,
        'images': images,
        'reviews': reviews,
    }
    return render(request, 'properties/property_detail.html', context)

@login_required
def book_property(request, property_id):
    if request.user.user_type != 'tenant':
        messages.error(request, 'Only tenants can book properties.')
        return redirect('home')
    
    property_obj = get_object_or_404(Properties, pk=property_id, status='available')
    tenant = get_object_or_404(Tenants, user=request.user)
    
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.tenant = tenant
            booking.property = property_obj
            # Compute duration (in months) from start and end dates
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')
            # Default values
            months = 0
            total = 0

            if start_date and end_date and end_date > start_date:
                # total number of days between dates
                days = (end_date - start_date).days

                # If the rental is less than 30 days, charge day-wise (rent/30 per day)
                if days < 30:
                    per_day = float(property_obj.rent_amount) / 30.0
                    total = round(per_day * max(1, days), 2)
                    months = 0
                else:
                    # Compute calendar-aware year/month/day delta
                    import calendar

                    y = end_date.year - start_date.year
                    m = end_date.month - start_date.month
                    d = end_date.day - start_date.day

                    if d < 0:
                        # borrow days from the previous month of end_date
                        prev_month = end_date.month - 1 if end_date.month > 1 else 12
                        prev_year = end_date.year if end_date.month > 1 else end_date.year - 1
                        days_in_prev_month = calendar.monthrange(prev_year, prev_month)[1]
                        d += days_in_prev_month
                        m -= 1

                    if m < 0:
                        m += 12
                        y -= 1

                    total_months = y * 12 + m
                    if total_months < 1:
                        total_months = 1

                    # charge full months at rent and any leftover days prorated
                    per_day = float(property_obj.rent_amount) / 30.0
                    total = round(float(property_obj.rent_amount) * total_months + per_day * d, 2)
                    months = total_months

            # Persist computed values
            booking.duration_months = months
            booking.total_amount = total
            booking.security_deposit = property_obj.security_deposit or property_obj.rent_amount

            booking.save()
            booking.save()
            
            # Create notification for tenant (booking created) -- skip notifying the actor
            if booking.tenant and booking.tenant.user != request.user:
                create_notification(
                    user=booking.tenant.user,
                    notification_type='push',
                    title='Booking Confirmed',
                    message_text=f'Your booking for {property_obj.title} has been created. Awaiting owner approval.',
                    related_entity_type='booking',
                    related_entity_id=booking.booking_id
                )

            # Create notification for owner (new booking request) -- skip notifying the actor
            if property_obj.owner and property_obj.owner.user != request.user:
                create_notification(
                    user=property_obj.owner.user,
                    notification_type='push',
                    title='New Booking Request',
                    message_text=f'New booking request for {property_obj.title} from {request.user.first_name} {request.user.last_name}.',
                    related_entity_type='booking',
                    related_entity_id=booking.booking_id
                )
            
            messages.success(request, 'Property booked successfully!')
            return redirect('tenant_dashboard')
    else:
        form = BookingForm()
    
    context = {
        'property': property_obj,
        'form': form,
    }
    return render(request, 'bookings/book_property.html', context)

@login_required
def confirm_booking(request, booking_id):
    if request.user.user_type != 'owner':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    try:
        booking = get_object_or_404(Bookings, pk=booking_id, property__owner__user=request.user)
        
        if booking.booking_status == 'pending':
            booking.booking_status = 'confirmed'
            booking.save()
            
            booking.property.status = 'occupied'
            booking.property.save()

            # Create a single initial pending payment when booking is confirmed.
            try:
                from django.utils import timezone

                today = timezone.now().date()
                # Only create an initial payment if none exist yet for this booking
                if not Payments.objects.filter(booking=booking).exists():
                    total_days = (booking.end_date - booking.start_date).days
                    if total_days < 30:
                        per_day = float(booking.property.rent_amount) / 30.0
                        amount = round(per_day * max(1, total_days), 2)
                    else:
                        amount = float(booking.property.rent_amount)

                    due_date = booking.start_date if booking.start_date >= today else today
                    payment = Payments.objects.create(
                        booking=booking,
                        tenant=booking.tenant,
                        owner=booking.property.owner,
                        amount=amount,
                        due_date=due_date,
                        payment_status='pending'
                    )
                    # Notify tenant about the pending payment (tenant only)
                    try:
                        if payment.tenant and payment.tenant.user:
                            create_notification(
                                user=payment.tenant.user,
                                notification_type='email',
                                title='Payment Due',
                                message_text=f'Your payment of BDT {payment.amount} is due on {payment.due_date.strftime("%b %d, %Y")}.',
                                related_entity_type='payment',
                                related_entity_id=payment.payment_id
                            )
                    except Exception:
                        pass
            except Exception:
                pass
            
            # Create notification for tenant (booking confirmed by owner) -- don't notify the actor
            if booking.tenant and booking.tenant.user != request.user:
                create_notification(
                    user=booking.tenant.user,
                    notification_type='push',
                    title='Booking Confirmed',
                    message_text=f'Your booking for {booking.property.title} has been confirmed by the owner!',
                    related_entity_type='booking',
                    related_entity_id=booking.booking_id
                )
            
            return redirect('owner_dashboard')
    except Bookings.DoesNotExist:
        messages.error(request, 'Booking not found or you do not have permission.')
        return redirect('owner_dashboard')


@login_required
def cancel_booking(request, booking_id):
    # Only accept POST requests for cancellation
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('home')

    try:
        booking = Bookings.objects.get(pk=booking_id)
    except Bookings.DoesNotExist:
        messages.error(request, 'Booking not found.')
        return redirect('home')

    # Determine if the requester is authorized (owner of property or the tenant)
    user = request.user
    redirect_target = 'home'
    authorized = False

    if user.user_type == 'owner' and hasattr(user, 'owner'):
        if booking.property.owner.user == user:
            authorized = True
            redirect_target = 'owner_dashboard'

    if user.user_type == 'tenant' and hasattr(user, 'tenant'):
        if booking.tenant.user == user:
            authorized = True
            redirect_target = 'tenant_dashboard'

    if not authorized:
        messages.error(request, 'Booking not found or you do not have permission.')
        return redirect('home')

    if booking.booking_status == 'pending':
        booking.booking_status = 'cancelled'
        booking.save()
        # If property was marked occupied by this booking, free it up
        try:
            prop = booking.property
            if prop.status == 'occupied':
                prop.status = 'available'
                prop.save()
        except Exception:
            pass
        
        # Create notification for both tenant and owner (booking cancelled) -- skip actor
        cancelled_by = f"{user.first_name} {user.last_name}"
        if booking.tenant and booking.tenant.user != request.user:
            create_notification(
                user=booking.tenant.user,
                notification_type='push',
                title='Booking Cancelled',
                message_text=f'Booking for {booking.property.title} has been cancelled by {cancelled_by}.',
                related_entity_type='booking',
                related_entity_id=booking.booking_id
            )
        if booking.property and booking.property.owner and booking.property.owner.user != request.user:
            create_notification(
                user=booking.property.owner.user,
                notification_type='push',
                title='Booking Cancelled',
                message_text=f'Booking for {booking.property.title} from {booking.tenant.user.first_name} has been cancelled.',
                related_entity_type='booking',
                related_entity_id=booking.booking_id
            )

        messages.success(request, f'Booking #{booking.booking_id} has been cancelled.')
    else:
        messages.warning(request, 'This booking is already processed.')

    return redirect(redirect_target)
@login_required
def submit_complaint(request):
    if request.user.user_type != 'tenant':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    try:
        tenant = request.user.tenant
    except:
        messages.error(request, 'Tenant profile not found.')
        return redirect('tenant_dashboard')

    try:
        active_booking = Bookings.objects.filter(
            tenant=tenant,
            booking_status__in=['confirmed', 'completed']
        ).latest('start_date')
        property_obj = active_booking.property
    except Bookings.DoesNotExist:
        messages.error(request, 'No active booking found.')
        return redirect('tenant_dashboard')

    if request.method == 'POST':
        form = ComplaintRequestForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.tenant = tenant
            complaint.property = property_obj
            complaint.save()
            
            # Create notification for owner (complaint submitted) -- skip actor
            if property_obj.owner and property_obj.owner.user != request.user:
                create_notification(
                    user=property_obj.owner.user,
                    notification_type='push',
                    title='New Complaint',
                    message_text=f'{tenant.user.first_name} has submitted a complaint: {complaint.title}',
                    related_entity_type='complaint',
                    related_entity_id=complaint.complaint_id
                )
            
            messages.success(request, 'Complaint submitted successfully!')
            return redirect('tenant_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ComplaintRequestForm()
    
    return render(request, 'complaints/submit_complaint.html', {
        'form': form,
        'property': property_obj
    })

@login_required
def owner_complaints(request):
    if request.user.user_type != 'owner':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    try:
        owner = request.user.owner
    except:
        messages.error(request, 'Owner profile not found.')
        return redirect('login')
    
    owner_properties = Properties.objects.filter(owner=owner)
    # list of tenants who have complaints on owner's properties
    tenants_with_complaints = Tenants.objects.filter(complaints__property__in=owner_properties).distinct()

    # Optionally filter by tenant via GET parameter
    tenant_id = request.GET.get('tenant_id')
    if tenant_id:
        try:
            selected_tenant = Tenants.objects.get(tenant_id=tenant_id)
            complaints = ComplaintsRequests.objects.filter(property__in=owner_properties, tenant=selected_tenant).order_by('-created_at')
        except Tenants.DoesNotExist:
            selected_tenant = None
            complaints = ComplaintsRequests.objects.filter(property__in=owner_properties).order_by('-created_at')
    else:
        selected_tenant = None
        complaints = ComplaintsRequests.objects.filter(property__in=owner_properties).order_by('-created_at')
    
    if request.method == 'POST' and 'complaint_id' in request.POST:
        complaint_id = request.POST.get('complaint_id')
        try:
            complaint = ComplaintsRequests.objects.get(
                complaint_id=complaint_id,
                property__in=owner_properties
            )
            form = ComplaintResolutionForm(request.POST, instance=complaint)
            if form.is_valid():
                resolved_complaint = form.save(commit=False)
                
                if resolved_complaint.status == 'resolved' and not resolved_complaint.resolved_at:
                    resolved_complaint.resolved_at = timezone.now()
                
                if resolved_complaint.status != 'resolved':
                    resolved_complaint.resolved_at = None
                
                resolved_complaint.save()
                messages.success(request, f'Complaint #{complaint_id} updated successfully!')
                return redirect('owner_complaints')
            else:
                messages.error(request, 'Please correct the errors below.')
        except ComplaintsRequests.DoesNotExist:
            messages.error(request, 'Complaint not found.')
    
    total_complaints = complaints.count()
    open_complaints = complaints.filter(status='open').count()
    in_progress_complaints = complaints.filter(status='in-progress').count()
    resolved_complaints = complaints.filter(status='resolved').count()
    
    high_priority_complaints = complaints.filter(priority='high', status__in=['open', 'in-progress'])
    
    context = {
        'owner': owner,
        'complaints': complaints,
        'total_complaints': total_complaints,
        'open_complaints': open_complaints,
        'in_progress_complaints': in_progress_complaints,
        'resolved_complaints': resolved_complaints,
        'high_priority_complaints': high_priority_complaints,
        'tenants_with_complaints': tenants_with_complaints,
        'selected_tenant': selected_tenant,
    }
    
    return render(request, 'complaints/owner_complaints.html', context)

@login_required
def quick_resolve_complaint(request, complaint_id):
    if request.user.user_type != 'owner':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    try:
        owner = request.user.owner
        complaint = get_object_or_404(
            ComplaintsRequests, 
            complaint_id=complaint_id,
            property__owner=owner
        )
        
        complaint.status = 'resolved'
        complaint.resolution_notes = 'Resolved by owner.'
        complaint.resolved_at = timezone.now()
        complaint.save()
        
        messages.success(request, f'Complaint #{complaint_id} marked as resolved!')
    except Exception as e:
        messages.error(request, f'Error resolving complaint: {str(e)}')
    
    return redirect('owner_complaints')

@login_required
def submit_review(request, booking_id):
    if request.user.user_type != 'tenant':
        messages.error(request, 'Only tenants can submit reviews.')
        return redirect('home')
    
    booking = get_object_or_404(Bookings, pk=booking_id, tenant__user=request.user)
    
    if ReviewsRatings.objects.filter(booking=booking).exists():
        messages.error(request, 'You have already reviewed this property.')
        return redirect('tenant_dashboard')
    
    if request.method == 'POST':
        form = ReviewRatingForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.tenant = booking.tenant
            review.property = booking.property
            review.booking = booking
            review.save()
            
            messages.success(request, 'Review submitted successfully!')
            return redirect('tenant_dashboard')
    else:
        form = ReviewRatingForm()
    
    context = {
        'booking': booking,
        'form': form,
    }
    return render(request, 'reviews/submit_review.html', context)

@login_required
def send_message(request):
    if request.method == 'POST':
        form = MessageForm(request.POST, user=request.user)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.save()
            
            # Create notification for receiver (new message received) -- skip actor
            if message.receiver and message.receiver != request.user:
                create_notification(
                    user=message.receiver,
                    notification_type='push',
                    title='New Message',
                    message_text=f'You received a message from {request.user.first_name} {request.user.last_name}',
                    related_entity_type='message',
                    related_entity_id=message.message_id
                )
            
            messages.success(request, 'Message sent successfully!')
            return redirect('tenant_dashboard' if request.user.user_type == 'tenant' else 'owner_dashboard')
    else:
        form = MessageForm(user=request.user)
    
    return render(request, 'messages/send_message.html', {'form': form})

@login_required
def inbox(request):
    received_messages = Messages.objects.filter(receiver=request.user).order_by('-sent_at')
    sent_messages = Messages.objects.filter(sender=request.user).order_by('-sent_at')
    
    context = {
        'received_messages': received_messages,
        'sent_messages': sent_messages,
    }
    return render(request, 'messages/inbox.html', context)

# NEW VIEWS ADDED
@login_required
def owner_booking_list(request):
    if request.user.user_type != 'owner':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    owner = get_object_or_404(Owners, user=request.user)
    bookings = Bookings.objects.filter(property__owner=owner).order_by('-created_at')
    
    context = {
        'bookings': bookings,
        'owner': owner,
    }
    return render(request, 'owner/owner_booking_list.html', context)

@login_required
def owner_payments(request):
    if request.user.user_type != 'owner':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    owner = get_object_or_404(Owners, user=request.user)
    payments = Payments.objects.filter(owner=owner).order_by('-created_at')
    
    context = {
        'payments': payments,
        'owner': owner,
    }
    # Render the owner payments template (file at templates/owner_payments.html)
    return render(request, 'owner_payments.html', context)


@login_required
def confirm_payment(request, payment_id):
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('owner_payments')

    if request.user.user_type != 'owner':
        messages.error(request, 'Access denied.')
        return redirect('home')

    try:
        owner = request.user.owner
    except Exception:
        messages.error(request, 'Owner profile not found.')
        return redirect('owner_payments')

    try:
        payment = Payments.objects.get(pk=payment_id, owner=owner)
        payment.payment_status = 'completed'
        if not payment.payment_date:
            payment.payment_date = timezone.now().date()
        payment.save()
        # After marking received, create next month's pending payment if booking still has remainder
        created_next = False
        try:
            booking = payment.booking
            if booking:
                # compute next due date: use payment.due_date if present else payment.payment_date
                from django.utils import timezone as _tz
                import calendar as _calendar

                base_date = payment.due_date or payment.payment_date or _tz.now().date()
                month = base_date.month + 1
                year = base_date.year + (month - 1) // 12
                month = (month - 1) % 12 + 1
                day = min(base_date.day, _calendar.monthrange(year, month)[1])
                next_due = base_date.replace(year=year, month=month, day=day)

                # Only create if next_due is on or before booking.end_date
                # and we haven't already created payments equal to the booking duration.
                try:
                    expected_count = int(booking.duration_months) if getattr(booking, 'duration_months', None) and int(booking.duration_months) > 0 else 1
                except Exception:
                    expected_count = 1

                current_count = Payments.objects.filter(booking=booking).count()

                if booking.end_date and next_due <= booking.end_date and current_count < expected_count:
                    # avoid duplicate pending for same due_date
                    exists = Payments.objects.filter(booking=booking, due_date=next_due, payment_status='pending').exists()
                    if not exists:
                        created_payment = Payments.objects.create(
                            booking=booking,
                            tenant=booking.tenant,
                            owner=booking.property.owner,
                            amount=booking.property.rent_amount,
                            due_date=next_due,
                            payment_status='pending'
                        )
                        created_next = True
                        # Notify tenant about the newly created pending payment (tenant only)
                        try:
                            if created_payment.tenant and created_payment.tenant.user:
                                create_notification(
                                    user=created_payment.tenant.user,
                                    notification_type='email',
                                    title='Payment Due',
                                    message_text=f'Your payment of BDT {created_payment.amount} is due on {created_payment.due_date.strftime("%b %d, %Y")}.',
                                    related_entity_type='payment',
                                    related_entity_id=created_payment.payment_id
                                )
                        except Exception:
                            pass
        except Exception:
            created_next = False

        # Notify tenant that owner has confirmed the payment
        try:
            if payment.tenant and payment.tenant.user:
                if created_next and 'next_due' in locals():
                    msg = f'Your payment of BDT {payment.amount} has been confirmed by the owner. Next due: {next_due.strftime("%b %d, %Y")}.'
                else:
                    msg = f'Your payment of BDT {payment.amount} has been confirmed by the owner.'

                create_notification(
                    user=payment.tenant.user,
                    notification_type='push',
                    title='Payment Confirmed',
                    message_text=msg,
                    related_entity_type='payment',
                    related_entity_id=payment.payment_id
                )
        except Exception:
            pass
        messages.success(request, f'Payment #{payment.payment_id} marked as received.')
    except Payments.DoesNotExist:
        messages.error(request, 'Payment not found.')

    return redirect('owner_payments')


@login_required
def export_payments_csv(request):
    if request.user.user_type != 'owner':
        messages.error(request, 'Access denied.')
        return redirect('home')

    try:
        owner = request.user.owner
    except Exception:
        messages.error(request, 'Owner profile not found.')
        return redirect('owner_payments')

    payments = Payments.objects.filter(owner=owner).order_by('-created_at')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="owner_payments.csv"'

    writer = csv.writer(response)
    writer.writerow(['Payment ID', 'Booking ID', 'Property', 'Tenant', 'Amount', 'Payment Date', 'Status', 'Transaction ID'])
    for p in payments:
        tenant_name = p.tenant.user.get_full_name() if hasattr(p.tenant, 'user') else ''
        writer.writerow([p.payment_id, p.booking.booking_id if p.booking else '', p.booking.property.title if p.booking and p.booking.property else '', tenant_name, str(p.amount), p.payment_date or '', p.payment_status, p.transaction_id or ''])

    return response


@login_required
def export_payments_pdf(request):
    if request.user.user_type != 'owner':
        messages.error(request, 'Access denied.')
        return redirect('home')

    if not REPORTLAB_AVAILABLE:
        messages.error(request, 'PDF export not available (reportlab not installed).')
        return redirect('owner_payments')

    try:
        owner = request.user.owner
    except Exception:
        messages.error(request, 'Owner profile not found.')
        return redirect('owner_payments')

    payments = Payments.objects.filter(owner=owner).order_by('-created_at')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="owner_payments.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    y = height - 40
    p.setFont('Helvetica-Bold', 14)
    p.drawString(40, y, f'Payments for {owner.user.get_full_name()}')
    y -= 30
    p.setFont('Helvetica', 10)
    headers = ['PID', 'BID', 'Property', 'Tenant', 'Amount', 'Date', 'Status']
    p.drawString(40, y, ' | '.join(headers))
    y -= 20

    for pmt in payments:
        if y < 60:
            p.showPage()
            y = height - 40
            p.setFont('Helvetica', 10)
        tenant_name = pmt.tenant.user.get_full_name() if hasattr(pmt.tenant, 'user') else ''
        prop_title = pmt.booking.property.title if pmt.booking and pmt.booking.property else ''
        line = f"{pmt.payment_id} | {pmt.booking.booking_id if pmt.booking else ''} | {prop_title} | {tenant_name} | {pmt.amount} | {pmt.payment_date or ''} | {pmt.payment_status}"
        p.drawString(40, y, line[:200])
        y -= 14

    p.showPage()
    p.save()
    return response

@login_required
def delete_message(request, message_id):
    """Delete a message (sent or received)"""
    try:
        # User can delete messages they sent OR received
        message = get_object_or_404(
            Messages,
            pk=message_id
        )
        
        # Check if user is sender or receiver
        if message.sender != request.user and message.receiver != request.user:
            messages.error(request, 'You do not have permission to delete this message.')
            return redirect('inbox')
        
        message.delete()
        messages.success(request, 'Message deleted successfully!')
        
    except Messages.DoesNotExist:
        messages.error(request, 'Message not found.')
    
    return redirect('inbox')

@login_required
def view_notifications(request):
    """View all notifications for the logged-in user"""
    notifications = Notifications.objects.filter(user=request.user).order_by('-sent_at')
    unread_count = notifications.filter(is_read=False).count()
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
    }
    return render(request, 'notifications/view_notifications.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read and redirect back to notifications."""
    try:
        notification = Notifications.objects.get(notification_id=notification_id, user=request.user)
    except Notifications.DoesNotExist:
        messages.error(request, 'Notification not found.')
        return redirect('view_notifications')

    if not notification.is_read:
        notification.is_read = True
        notification.save()

    # Try to redirect to related entity if provided (basic mapping), otherwise back to notifications
    rel_type = (notification.related_entity_type or '').lower() if notification.related_entity_type else ''
    rel_id = notification.related_entity_id

    if rel_type == 'message' and rel_id:
        return redirect('inbox')
    if rel_type == 'booking' and rel_id:
        return redirect('tenant_dashboard' if request.user.user_type == 'tenant' else 'owner_dashboard')
    if rel_type == 'payment' and rel_id:
        return redirect('tenant_dashboard' if request.user.user_type == 'tenant' else 'owner_payments')

    # Fallback
    return redirect('view_notifications')



#sslcommerz

# views.py (নিচের অংশে যোগ করুন)

# views.py - SSLCommerz views (Modified version)

import requests
import json
import time
from datetime import timedelta
from decimal import Decimal
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.timezone import now


@login_required
def initiate_sslcommerz_payment(request, booking_id):
    print(request)
    
    """SSLCommerz পেমেন্ট শুরু করুন"""
    if request.user.user_type != 'tenant':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    booking = get_object_or_404(Bookings, pk=booking_id, tenant__user=request.user)
    tenant = booking.tenant
    
    # Payment amount নির্ধারণ করুন
    payment_amount = booking.total_amount
    
    # SSLCommerz configuration (use settings values when available)
    sandbox = getattr(settings, 'SSLCOMMERZ_SANDBOX', getattr(settings, 'SSLCOMMERZ_IS_SANDBOX', True))
    store_id = getattr(settings, 'SSLCOMMERZ_STORE_ID', 'rhms695208c009a98')
    store_pass = getattr(settings, 'SSLCOMMERZ_STORE_PASSWORD', getattr(settings, 'SSLCOMMERZ_STORE_PASSWORD', 'qwerty'))
    currency = getattr(settings, 'SSLCOMMERZ_CURRENCY', 'BDT')
    
    # Use HTTPS to avoid redirects that drop POST payloads
    base_url = "https://sandbox.sslcommerz.com" if sandbox else "https://securepay.sslcommerz.com"
    
    # Generate transaction ID
    tran_id = f"RENT{booking.booking_id}{timezone.now().strftime('%Y%m%d%H%M%S')}"
    
    # Payment URLs
    success_url = request.build_absolute_uri(reverse('sslcommerz_success'))
    fail_url = request.build_absolute_uri(reverse('sslcommerz_fail'))
    cancel_url = request.build_absolute_uri(reverse('sslcommerz_cancel'))
    ipn_url = request.build_absolute_uri(reverse('sslcommerz_ipn'))
    
    # Customer information
    user = request.user
    customer_name = f"{user.first_name} {user.last_name}"
    customer_email = user.email
    customer_phone = user.phone or '01700000000'
    
    # Prepare payload for SSLCommerz
    payload = {
        'store_id': store_id,
        'store_passwd': store_pass,
        'total_amount': str(payment_amount),
        'currency': currency,
        'tran_id': tran_id,
        'success_url': success_url,
        'fail_url': fail_url,
        'cancel_url': cancel_url,
        'ipn_url': ipn_url,
        'cus_name': customer_name,
        'cus_email': customer_email,
        'cus_phone': customer_phone,
        'cus_add1': getattr(tenant, 'address', 'N/A'),
        'cus_add2': '',
        'cus_city': getattr(tenant, 'city', 'Dhaka'),
        'cus_state': '',
        'cus_postcode': '',
        'cus_country': 'Bangladesh',
        'cus_fax': '',
        'shipping_method': 'NO',
        'num_of_item': 1,
        'product_name': f"Booking #{booking.booking_id} - {booking.property.title}",
        'product_category': 'Rental Service',
        'product_profile': 'general',
       # 'value_a': str(booking.booking_id),  # Booking ID
        #'value_b': str(tenant.tenant_id),    # Tenant ID
       # 'value_c': str(request.tenant_id),     # User ID
       # 'value_d': 'rental_payment',         # Payment Type

    }
    # Send request with retries and timeout; SSL EOF or redirect can drop POST data
    max_retries = 3
    backoff = 1
    response = None
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(f"{base_url}/gwprocess/v4/api.php", data=payload, timeout=10)
            break
        except requests.exceptions.SSLError as e:
            last_exc = e
            if attempt == max_retries:
                break
            time.sleep(backoff)
            backoff *= 2
        except requests.exceptions.RequestException as e:
            last_exc = e
            if attempt == max_retries:
                break
            time.sleep(backoff)
            backoff *= 2

    if response is None:
        messages.error(request, f'Payment initiation failed: {str(last_exc)}')
        return redirect('tenant_dashboard')

    if response.status_code != 200:
        messages.error(request, f'Payment gateway error: HTTP {response.status_code}')
        return redirect('tenant_dashboard')

    try:
        response_data = response.json()
    except ValueError:
        messages.error(request, 'Payment gateway returned invalid JSON.')
        return redirect('tenant_dashboard')

    if response_data.get('status') != 'SUCCESS':
        error_msg = response_data.get('failedreason', response_data.get('error', 'Unknown error'))
        messages.error(request, f'Payment gateway error: {error_msg}')
        return redirect('tenant_dashboard')

    gateway_url = response_data.get('GatewayPageURL')
    session_key = response_data.get('sessionkey')

    # Reuse existing pending payment for this booking if available to avoid duplicates
    pending_payment = Payments.objects.filter(booking=booking, payment_status='pending').order_by('due_date').first()
    if pending_payment:
        payment = pending_payment
        payment.transaction_id = tran_id
        payment.payment_method = 'sslcommerz'
        # do not mark completed here; tenant is redirected to gateway
        payment.save()
    else:
        # Create payment record
        payment = Payments.objects.create(
            booking=booking,
            tenant=tenant,
            owner=booking.property.owner,
            amount=payment_amount,
            payment_method='sslcommerz',
            payment_status='pending',
            transaction_id=tran_id,
            due_date=(now().date())
        )
        # Notify tenant about the pending payment created for gateway transaction
        try:
            if payment.tenant and payment.tenant.user:
                create_notification(
                    user=payment.tenant.user,
                    notification_type='email',
                    title='Payment Created',
                    message_text=f'A payment of BDT {payment.amount} has been created and is pending. Due: {payment.due_date.strftime("%b %d, %Y")}.',
                    related_entity_type='payment',
                    related_entity_id=payment.payment_id
                )
        except Exception:
            pass

    # Save session info
    request.session['payment_session_key'] = session_key
    request.session['booking_id'] = booking.booking_id
    request.session['payment_id'] = payment.payment_id
    request.session['tran_id'] = tran_id

    if gateway_url:
        return redirect(gateway_url)
    else:
        messages.error(request, 'Payment gateway did not return redirect URL.')
        return redirect('tenant_dashboard')

@csrf_exempt
def sslcommerz_success(request):
    """SSLCommerz সফল পেমেন্ট হ্যান্ডলার"""
    val_id = request.POST.get('val_id') or request.GET.get('val_id')
    tran_id = request.POST.get('tran_id') or request.GET.get('tran_id')

    # If val_id is not provided, use tran_id from session
    if not val_id:
        val_id = request.session.get('tran_id', '')
    
    if not val_id:
        messages.error(request, 'Invalid payment response.')
        return redirect('tenant_dashboard')
    
    # SSLCommerz configuration
    sandbox = getattr(settings, 'SSLCOMMERZ_SANDBOX', True)
    store_id = getattr(settings, 'SSLCOMMERZ_STORE_ID', 'testbox')
    store_pass = getattr(settings, 'SSLCOMMERZ_STORE_PASSWORD', 'qwerty')
    
    base_url = "https://sandbox.sslcommerz.com" if sandbox else "https://securepay.sslcommerz.com"
    
    try:
        # Verify payment with SSLCommerz
        verify_url = f"{base_url}/validator/api/validationserverAPI.php"
        params = {
            'val_id': val_id,
            'store_id': store_id,
            'store_passwd': store_pass,
            'format': 'json'
        }
        
        response = requests.get(verify_url, params=params)
        
        if response.status_code == 200:
            verification_data = response.json()
            
            if verification_data.get('status') == 'VALID':
                # Get payment from database: prefer session, then transaction id, then booking
                payment = None
                payment_id = request.session.get('payment_id')
                booking_id = request.session.get('booking_id')

                if payment_id:
                    try:
                        payment = Payments.objects.get(pk=payment_id)
                    except Payments.DoesNotExist:
                        payment = None

                # Fallback to transaction id provided by gateway or request
                if payment is None and (verification_data.get('tran_id') or tran_id):
                    search_tran = verification_data.get('tran_id') or tran_id
                    try:
                        payment = Payments.objects.get(transaction_id=search_tran)
                    except Payments.DoesNotExist:
                        payment = None

                # Last resort: find recent pending payment for the booking
                if payment is None and booking_id:
                    try:
                        payment = Payments.objects.filter(booking__booking_id=booking_id, payment_status='pending').order_by('-payment_id').first()
                    except Exception:
                        payment = None

                if not payment:
                    messages.error(request, 'Payment record not found for this transaction.')
                else:
                    # Record transaction details from gateway
                    payment.transaction_id = verification_data.get('tran_id', tran_id)
                    if not payment.payment_date:
                        payment.payment_date = timezone.now().date()
                    payment.gateway_response = verification_data
                    payment.save()

                    # If booking duration is <= 30 days, auto-mark this payment completed.
                    booking_obj = payment.booking
                    try:
                        duration_days = (booking_obj.end_date - booking_obj.start_date).days if booking_obj and booking_obj.end_date and booking_obj.start_date else None
                    except Exception:
                        duration_days = None

                    if duration_days is not None and duration_days <= 30:
                        # Complete the payment immediately for short bookings
                        payment.payment_status = 'completed'
                        payment.save()

                        # Update booking status and property as necessary
                        try:
                            if booking_obj and booking_obj.booking_status == 'pending':
                                booking_obj.booking_status = 'confirmed'
                                booking_obj.save()
                            if booking_obj and booking_obj.property and booking_obj.property.status == 'available':
                                booking_obj.property.status = 'occupied'
                                booking_obj.property.save()
                        except Exception:
                            pass

                        # Notify tenant and owner about successful payment
                        try:
                            create_notification(
                                user=payment.tenant.user,
                                notification_type='push',
                                title='Payment Successful',
                                message_text=f'Your payment of BDT {payment.amount} has been completed successfully.',
                                related_entity_type='payment',
                                related_entity_id=payment.payment_id
                            )
                        except:
                            pass

                        try:
                            if booking_obj and booking_obj.property and booking_obj.property.owner:
                                create_notification(
                                    user=booking_obj.property.owner.user,
                                    notification_type='push',
                                    title='Payment Received',
                                    message_text=f'Payment of BDT {payment.amount} received from {booking_obj.tenant.user.first_name} for {booking_obj.property.title}.',
                                    related_entity_type='payment',
                                    related_entity_id=payment.payment_id
                                )
                        except:
                            pass

                        messages.success(request, 'Payment completed successfully!')
                    else:
                        # For multi-month bookings, keep as pending and ask owner to confirm
                        try:
                            create_notification(
                                user=payment.tenant.user,
                                notification_type='push',
                                title='Payment Recorded',
                                message_text=f'Your payment of BDT {payment.amount} has been recorded and is awaiting owner confirmation.',
                                related_entity_type='payment',
                                related_entity_id=payment.payment_id
                            )
                        except:
                            pass

                        try:
                            if booking_obj and booking_obj.property and booking_obj.property.owner:
                                create_notification(
                                    user=booking_obj.property.owner.user,
                                    notification_type='push',
                                    title='Payment Awaiting Confirmation',
                                    message_text=f'A payment of BDT {payment.amount} was submitted for {booking_obj.property.title}. Please confirm receipt.',
                                    related_entity_type='payment',
                                    related_entity_id=payment.payment_id
                                )
                        except:
                            pass

                        messages.success(request, 'Payment recorded. Waiting for owner confirmation.')
            else:
                messages.error(request, 'Payment verification failed.')
        else:
            messages.error(request, 'Payment verification service error.')
            
    except Exception as e:
        messages.error(request, f'Payment verification error: {str(e)}')
    
    # Clear session data
    session_keys = ['payment_session_key', 'booking_id', 'payment_id', 'tran_id']
    for key in session_keys:
        if key in request.session:
            del request.session[key]
    
    return redirect('tenant_dashboard')

@login_required
def sslcommerz_fail(request):
    """SSLCommerz ব্যর্থ পেমেন্ট হ্যান্ডলার"""
    error_msg = request.GET.get('error', 'Payment failed')
    messages.error(request, f'Payment failed: {error_msg}')
    
    # Update payment status
    payment_id = request.session.get('payment_id')
    if payment_id:
        try:
            payment = Payments.objects.get(pk=payment_id)
            payment.payment_status = 'failed'
            payment.gateway_response = dict(request.GET)
            payment.save()
        except:
            pass
    
    # Clear session
    session_keys = ['payment_session_key', 'booking_id', 'payment_id', 'tran_id']
    for key in session_keys:
        if key in request.session:
            del request.session[key]
    
    return redirect('tenant_dashboard')

@login_required
def sslcommerz_cancel(request):
    """SSLCommerz বাতিল পেমেন্ট হ্যান্ডলার"""
    messages.warning(request, 'Payment was cancelled.')
    
    # Update payment status
    payment_id = request.session.get('payment_id')
    if payment_id:
        try:
            payment = Payments.objects.get(pk=payment_id)
            payment.payment_status = 'cancelled'
            payment.gateway_response = dict(request.GET)
            payment.save()
        except:
            pass
    
    # Clear session
    session_keys = ['payment_session_key', 'booking_id', 'payment_id', 'tran_id']
    for key in session_keys:
        if key in request.session:
            del request.session[key]
    
    return redirect('tenant_dashboard')

def sslcommerz_ipn(request):
    """Instant Payment Notification (IPN) হ্যান্ডলার"""
    if request.method == 'POST':
        data = request.POST.dict()
        
        # Verify the IPN with SSLCommerz
        sandbox = getattr(settings, 'SSLCOMMERZ_SANDBOX', True)
        store_id = getattr(settings, 'SSLCOMMERZ_STORE_ID', 'testbox')
        store_pass = getattr(settings, 'SSLCOMMERZ_STORE_PASSWORD', 'qwerty')
        
        base_url = "https://sandbox.sslcommerz.com" if sandbox else "https://securepay.sslcommerz.com"
        
        # Get validation ID from data
        val_id = data.get('val_id')
        
        if val_id:
            try:
                verify_url = f"{base_url}/validator/api/validationserverAPI.php"
                params = {
                    'val_id': val_id,
                    'store_id': store_id,
                    'store_passwd': store_pass,
                    'format': 'json'
                }
                
                response = requests.get(verify_url, params=params)
                
                if response.status_code == 200:
                    verification = response.json()
                    
                    if verification.get('status') == 'VALID':
                        # Update payment
                        tran_id = verification.get('tran_id')
                        
                        try:
                            payment = Payments.objects.get(transaction_id=tran_id)
                            payment.payment_status = 'completed'
                            payment.payment_date = timezone.now().date()
                            payment.gateway_ipn_response = data
                            payment.save()
                            
                            # Update booking
                            booking = payment.booking
                            if booking.booking_status == 'pending':
                                booking.booking_status = 'confirmed'
                                booking.save()
                            
                            # Update property
                            if booking.property.status == 'available':
                                booking.property.status = 'occupied'
                                booking.property.save()
                                
                        except Payments.DoesNotExist:
                            pass
            except:
                pass
    print(request.user)
    return HttpResponse('IPN Received', status=200)