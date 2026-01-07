from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MinValueValidator, MaxValueValidator

# Choice Classes
class UserType(models.TextChoices):
    TENANT = 'tenant', 'Tenant'
    OWNER = 'owner', 'Owner'
    ADMIN = 'admin', 'Admin'

class UserStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    INACTIVE = 'inactive', 'Inactive'
    SUSPENDED = 'suspended', 'Suspended'

class PropertyType(models.TextChoices):
    APARTMENT = 'apartment', 'Apartment'
    HOUSE = 'house', 'House'
    VILLA = 'villa', 'Villa'
    CONDO = 'condo', 'Condominium'
    STUDIO = 'studio', 'Studio'

class PropertyStatus(models.TextChoices):
    AVAILABLE = 'available', 'Available'
    OCCUPIED = 'occupied', 'Occupied'
    MAINTENANCE = 'maintenance', 'Under Maintenance'

class BookingStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    CONFIRMED = 'confirmed', 'Confirmed'
    CANCELLED = 'cancelled', 'Cancelled'
    COMPLETED = 'completed', 'Completed'

class PaymentMethod(models.TextChoices):
    CARD = 'card', 'Credit/Debit Card'
    BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
    DIGITAL_WALLET = 'digital_wallet', 'Digital Wallet'
    CASH = 'cash' , 'Cash'

class PaymentStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'

class ComplaintType(models.TextChoices):
    COMPLAINT = 'complaint', 'Complaint'
    MAINTENANCE = 'maintenance', 'Maintenance Request'
    QUERY = 'query', 'General Query'

class PriorityType(models.TextChoices):
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'

class ComplaintStatus(models.TextChoices):
    OPEN = 'open', 'Open'
    IN_PROGRESS = 'in-progress', 'In Progress'
    RESOLVED = 'resolved', 'Resolved'

class NotificationType(models.TextChoices):
    EMAIL = 'email', 'Email'
    SMS = 'sms', 'SMS'
    PUSH = 'push', 'Push Notification'

# Custom User Manager
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', UserType.ADMIN)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)

# Main User Model - FIXED WITH ALL REQUIRED METHODS
class Users(AbstractBaseUser, PermissionsMixin):
    user_id = models.AutoField(primary_key=True)
    user_type = models.CharField(max_length=10, choices=UserType.choices, default=UserType.TENANT)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=UserStatus.choices, default=UserStatus.ACTIVE)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_short_name(self):
        return self.first_name
    
    def has_module_perms(self, app_label):
        """Does the user have permissions to view the app `app_label`?"""
        return True
    
    def has_perm(self, perm, obj=None):
        """Does the user have a specific permission?"""
        return True

# Tenant Model
class Tenants(models.Model):
    tenant_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(Users, on_delete=models.CASCADE, related_name='tenant')
    emergency_contact = models.CharField(max_length=20, blank=True, null=True)
    employment_status = models.CharField(max_length=50, blank=True, null=True)
    income_range = models.CharField(max_length=50, blank=True, null=True)
    rental_history = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'tenants'
    
    def __str__(self):
        return f"Tenant: {self.user.first_name} {self.user.last_name}"

# Owner Model
class Owners(models.Model):
    owner_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(Users, on_delete=models.CASCADE, related_name='owner')
    company_name = models.CharField(max_length=255, blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    bank_account_info = models.CharField(max_length=255, blank=True, null=True)
    verification_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected')
    ], default='pending')
    
    class Meta:
        db_table = 'owners'
    
    def __str__(self):
        return f"Owner: {self.user.first_name} {self.user.last_name}"

# Property Model
class Properties(models.Model):
    property_id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(Owners, on_delete=models.CASCADE, related_name='properties')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    property_type = models.CharField(max_length=20, choices=PropertyType.choices)
    bedrooms = models.IntegerField()
    bathrooms = models.DecimalField(max_digits=3, decimal_places=1)
    area_sqft = models.IntegerField(blank=True, null=True)
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    available_from = models.DateField()
    status = models.CharField(max_length=20, choices=PropertyStatus.choices, default=PropertyStatus.AVAILABLE)
    amenities = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'properties'
        verbose_name_plural = 'properties'
    
    def __str__(self):
        return f"{self.title} - {self.city}"

# Booking Model
class Bookings(models.Model):
    booking_id = models.AutoField(primary_key=True)
    tenant = models.ForeignKey(Tenants, on_delete=models.CASCADE, related_name='bookings')
    property = models.ForeignKey(Properties, on_delete=models.CASCADE, related_name='bookings')
    booking_date = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField()
    end_date = models.DateField()
    duration_months = models.IntegerField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2)
    booking_status = models.CharField(max_length=20, choices=BookingStatus.choices, default=BookingStatus.PENDING)
    special_requests = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'bookings'
    
    def __str__(self):
        return f"Booking #{self.booking_id} - {self.tenant.user.first_name}"

# Payment Model
class Payments(models.Model):
    payment_id = models.AutoField(primary_key=True)
    booking = models.ForeignKey(Bookings, on_delete=models.CASCADE, related_name='payments')
    tenant = models.ForeignKey(Tenants, on_delete=models.CASCADE, related_name='payments')
    owner = models.ForeignKey(Owners, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(blank=True, null=True)
    due_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, blank=True, null=True)
    transaction_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    receipt_url = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payments'
    
    def __str__(self):
        return f"Payment #{self.payment_id} - ${self.amount}"

# Complaint/Request Model
class ComplaintsRequests(models.Model):
    complaint_id = models.AutoField(primary_key=True)
    tenant = models.ForeignKey(Tenants, on_delete=models.CASCADE, related_name='complaints')
    property = models.ForeignKey(Properties, on_delete=models.CASCADE, related_name='complaints')
    type = models.CharField(max_length=20, choices=ComplaintType.choices)
    title = models.CharField(max_length=255)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PriorityType.choices, default=PriorityType.LOW)
    status = models.CharField(max_length=20, choices=ComplaintStatus.choices, default=ComplaintStatus.OPEN)
    assigned_to = models.ForeignKey(Users, on_delete=models.SET_NULL, blank=True, null=True, related_name='assigned_complaints')
    resolution_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'complaints_requests'
    
    def __str__(self):
        return f"Complaint: {self.title}"

# Review/Rating Model
class ReviewsRatings(models.Model):
    review_id = models.AutoField(primary_key=True)
    tenant = models.ForeignKey(Tenants, on_delete=models.CASCADE, related_name='reviews')
    property = models.ForeignKey(Properties, on_delete=models.CASCADE, related_name='reviews')
    booking = models.ForeignKey(Bookings, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    review_text = models.TextField(blank=True, null=True)
    owner_response = models.TextField(blank=True, null=True)
    response_date = models.DateTimeField(blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'reviews_ratings'
    
    def __str__(self):
        return f"Review #{self.review_id} - Rating: {self.rating}"

# Message Model
class Messages(models.Model):
    message_id = models.AutoField(primary_key=True)
    sender = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='received_messages')
    property = models.ForeignKey(Properties, on_delete=models.CASCADE, related_name='messages', blank=True, null=True)
    message_text = models.TextField()
    attachment_url = models.CharField(max_length=255, blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'messages'
    
    def __str__(self):
        return f"Message from {self.sender.first_name} to {self.receiver.first_name}"

# Notification Model
class Notifications(models.Model):
    notification_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=10, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)
    related_entity_type = models.CharField(max_length=50, blank=True, null=True)
    related_entity_id = models.IntegerField(blank=True, null=True)
    
    class Meta:
        db_table = 'notifications'
    
    def __str__(self):
        return f"Notification: {self.title}"

# Property Image Model
class PropertyImages(models.Model):
    image_id = models.AutoField(primary_key=True)
    property = models.ForeignKey(Properties, on_delete=models.CASCADE, related_name='images')
    image_url = models.ImageField(upload_to='property_images/')
    caption = models.CharField(max_length=255, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'property_images'
        
    
    def __str__(self):
        return f"Image for {self.property.title}"