# forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import *

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=6
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Users
        fields = ['user_type', 'email', 'first_name', 'last_name', 'phone']
        widgets = {
            'user_type': forms.Select(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Users.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        
        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match")
        
        return cleaned_data

class UserLoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = Users
        fields = ['first_name', 'last_name', 'phone', 'profile_picture']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }

class TenantProfileForm(forms.ModelForm):
    class Meta:
        model = Tenants
        fields = ['emergency_contact', 'employment_status', 'income_range', 'rental_history']
        widgets = {
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'employment_status': forms.TextInput(attrs={'class': 'form-control'}),
            'income_range': forms.TextInput(attrs={'class': 'form-control'}),
            'rental_history': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class OwnerProfileForm(forms.ModelForm):
    class Meta:
        model = Owners
        fields = ['company_name', 'tax_id', 'bank_account_info']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_info': forms.TextInput(attrs={'class': 'form-control'}),
        }

class PropertyForm(forms.ModelForm):
    class Meta:
        model = Properties
        fields = [
            'title', 'description', 'address', 'city', 'state', 'zip_code',
            'property_type', 'bedrooms', 'bathrooms', 'area_sqft', 'rent_amount',
            'security_deposit', 'available_from', 'amenities'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control'}),
            'property_type': forms.Select(attrs={'class': 'form-control'}),
            'bedrooms': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'bathrooms': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0.5'}),
            'area_sqft': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'rent_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'security_deposit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'available_from': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amenities': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean_rent_amount(self):
        rent_amount = self.cleaned_data.get('rent_amount')
        if rent_amount <= 0:
            raise ValidationError("Rent amount must be positive")
        return rent_amount
    
    def clean_available_from(self):
        available_from = self.cleaned_data.get('available_from')
        if available_from and available_from < timezone.now().date():
            raise ValidationError("Available date cannot be in the past")
        return available_from
    
    def clean_bedrooms(self):
        bedrooms = self.cleaned_data.get('bedrooms')
        if bedrooms and bedrooms < 0:
            raise ValidationError("Number of bedrooms cannot be negative")
        return bedrooms

class PropertySearchForm(forms.Form):
    PROPERTY_TYPE_CHOICES = [
        ('', 'Any Type'),
        ('apartment', 'Apartment'),
        ('house', 'House'),
        ('villa', 'Villa'),
        ('condo', 'Condominium'),
        ('studio', 'Studio'),
    ]
    address = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter address or place (e.g. Banani, Gulshan)'
        })
    )

    property_type = forms.ChoiceField(
        choices=PROPERTY_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    min_rent = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min amount',
            'step': '0.01'
        })
    )

    max_rent = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max amount',
            'step': '0.01'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        min_rent = cleaned_data.get('min_rent')
        max_rent = cleaned_data.get('max_rent')

        if min_rent and max_rent and min_rent > max_rent:
            raise ValidationError("Minimum amount cannot be greater than maximum amount")
        
        return cleaned_data

class BookingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.property = kwargs.pop('property', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Bookings
        # duration_months is computed server-side from start/end dates
        fields = ['start_date', 'end_date', 'special_requests']
        widgets = {
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'special_requests': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError("End date must be after start date")

            if start_date < timezone.now().date():
                raise ValidationError("Start date cannot be in the past")

        if self.property and start_date:
            if start_date < self.property.available_from:
                raise ValidationError(f"Start date cannot be before the property's available date ({self.property.available_from})")

        return cleaned_data

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payments
        fields = ['amount', 'payment_method', 'due_date']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise ValidationError("Payment amount must be positive")
        return amount
    
    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date < timezone.now().date():
            raise ValidationError("Due date cannot be in the past")
        return due_date

class ComplaintRequestForm(forms.ModelForm):
    class Meta:
        model = ComplaintsRequests
        fields = ['type', 'title', 'description', 'priority']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if len(title) < 5:
            raise ValidationError("Title must be at least 5 characters long")
        return title

class ComplaintResolutionForm(forms.ModelForm):
    class Meta:
        model = ComplaintsRequests
        fields = ['status', 'resolution_notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'resolution_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class ReviewRatingForm(forms.ModelForm):
    class Meta:
        model = ReviewsRatings
        fields = ['rating', 'review_text']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': 1, 
                'max': 5
            }),
            'review_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
    
    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating < 1 or rating > 5:
            raise ValidationError("Rating must be between 1 and 5")
        return rating
    
    def clean_review_text(self):
        review_text = self.cleaned_data.get('review_text')
        if review_text and len(review_text) < 10:
            raise ValidationError("Review must be at least 10 characters long")
        return review_text

class OwnerResponseForm(forms.ModelForm):
    class Meta:
        model = ReviewsRatings
        fields = ['owner_response']
        widgets = {
            'owner_response': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class MessageForm(forms.ModelForm):
    class Meta:
        model = Messages
        fields = ['receiver', 'property', 'message_text']
        widgets = {
            'receiver': forms.Select(attrs={'class': 'form-control'}),
            'property': forms.Select(attrs={'class': 'form-control'}),
            'message_text': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Type your message here...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        # Accept an optional `user` kwarg to customize receiver choices
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Base recipient queryset: exclude admins
        qs = Users.objects.exclude(user_type='admin')
        # If we have the current user, exclude self and limit by opposite type
        if user is not None:
            qs = qs.exclude(pk=user.pk)
            if getattr(user, 'user_type', None) == 'tenant':
                qs = qs.filter(user_type='owner')
            elif getattr(user, 'user_type', None) == 'owner':
                qs = qs.filter(user_type='tenant')

        self.fields['receiver'].queryset = qs

        # Filter properties to only show available ones
        self.fields['property'].queryset = Properties.objects.filter(
            status='available'
        )
    
    def clean_message_text(self):
        message_text = self.cleaned_data.get('message_text')
        if len(message_text.strip()) < 1:
            raise ValidationError("Message cannot be empty")
        return message_text

class PropertyImageForm(forms.ModelForm):
    class Meta:
        model = PropertyImages
        fields = ['image_url', 'caption', 'is_primary']
        widgets = {
            'image_url': forms.FileInput(attrs={'class': 'form-control'}),
            'caption': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter image caption'
            }),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class AdminUserManagementForm(forms.ModelForm):
    class Meta:
        model = Users
        fields = ['user_type', 'email', 'first_name', 'last_name', 'phone', 'status']
        widgets = {
            'user_type': forms.Select(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

class AdminPropertyManagementForm(forms.ModelForm):
    class Meta:
        model = Properties
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

# Filter Forms for Admin
class BookingFilterForm(forms.Form):
    STATUS_CHOICES = [
        ('', 'All Status'),
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES, 
        required=False, 
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    start_date_from = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={
            'class': 'form-control', 
            'type': 'date'
        })
    )
    
    start_date_to = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={
            'class': 'form-control', 
            'type': 'date'
        })
    )

class PaymentFilterForm(forms.Form):
    STATUS_CHOICES = [
        ('', 'All Status'),
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES, 
        required=False, 
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    payment_date_from = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={
            'class': 'form-control', 
            'type': 'date'
        })
    )
    
    payment_date_to = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={
            'class': 'form-control', 
            'type': 'date'
        })
    )

# Bulk Action Forms
class BulkActionForm(forms.Form):
    ACTION_CHOICES = [
        ('', 'Select Action'),
        ('activate', 'Activate Selected'),
        ('deactivate', 'Deactivate Selected'),
        ('delete', 'Delete Selected'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES, 
        required=False, 
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    selected_ids = forms.CharField(widget=forms.HiddenInput())

class ReportGenerationForm(forms.Form):
    REPORT_TYPE_CHOICES = [
        ('booking', 'Booking Report'),
        ('payment', 'Payment Report'),
        ('property', 'Property Report'),
        ('user', 'User Report'),
    ]
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPE_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control', 
            'type': 'date'
        })
    )
    
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control', 
            'type': 'date'
        })
    )
    
    format = forms.ChoiceField(
        choices=[('pdf', 'PDF'), ('excel', 'Excel')], 
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise ValidationError("Start date cannot be after end date")
        
        return cleaned_data

# Custom form for login without ModelForm
class SimpleLoginForm(forms.Form):
    email = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )

#sslcommerz
# payments/sslcommerz_form.py
from django import forms

class SSLCommerzPaymentForm(forms.Form):
    booking_id = forms.IntegerField(widget=forms.HiddenInput())
    amount = forms.DecimalField(max_digits=10, decimal_places=2, widget=forms.HiddenInput())
    customer_name = forms.CharField(max_length=255, widget=forms.HiddenInput())
    customer_email = forms.EmailField(widget=forms.HiddenInput())
    customer_phone = forms.CharField(max_length=20, widget=forms.HiddenInput())
    customer_address = forms.CharField(max_length=255, required=False, widget=forms.HiddenInput())
    customer_city = forms.CharField(max_length=100, required=False, widget=forms.HiddenInput())