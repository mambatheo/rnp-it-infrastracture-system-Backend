import uuid
from django.db import models
from equipment.models import DPU, Region , Unit
from django.utils.translation import gettext as _
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.validators import MaxLengthValidator, MinLengthValidator


class UserManager(BaseUserManager):

    def create_user(self, email, first_name, last_name, phone_number=None, password=None, dpu=None, region=None, unit=None, **extra_fields):

        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            dpu=dpu,
            region=region,
            unit=unit,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, password=None, phone_number=None, **extra_fields):
        user = self.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            password=password,
            role=User.ADMIN,
            **extra_fields,
        )
        user.is_active = True
        user.is_staff = True
        user.is_admin = True
        user.is_superuser = True
        user.is_first_login = False  # Superusers are exempt from forced password change
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    TECHNICIAN = 'TECHNICIAN'
    IT_STAFF = 'IT_STAFF'
    USER = 'USER'
    ADMIN = 'ADMIN'

    ROLE_CHOICES = [
        (TECHNICIAN, 'Technician'),
        (IT_STAFF, 'IT Staff'),
        (USER, 'User'),
        (ADMIN, 'Admin'),
    ]

    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, blank=True, null=True)
    email = models.EmailField(_("email address"), max_length=255, unique=True)
    first_name = models.CharField(_("first name"), max_length=100)
    last_name = models.CharField(_("last name"), max_length=100)
    phone_number = models.CharField(
        _("phone number"),
        max_length=10,
        unique=True,
        blank=True,
        null=True,
        validators=[MinLengthValidator(10), MaxLengthValidator(10)]
    )
    dpu    = models.ForeignKey("equipment.dpu",    on_delete=models.SET_NULL, null=True, blank=True, related_name="admin_dpu")
    region = models.ForeignKey("equipment.region", on_delete=models.SET_NULL, null=True, blank=True, related_name="admin_region")
    unit   = models.ForeignKey("equipment.unit",   on_delete=models.SET_NULL, null=True, blank=True, related_name="admin_unit")
    failed_login_attempts = models.IntegerField(_("failed login attempts"), default=0)
    is_locked = models.BooleanField(_("is locked"), default=False)
    locked_until = models.DateTimeField(_("locked until"), null=True, blank=True)
    is_active = models.BooleanField(_("is active"), default=False)  
    is_staff = models.BooleanField(_("staff"), default=False)
    is_admin = models.BooleanField(_("admin"), default=False)
    is_first_login = models.BooleanField(_("first login"), default=True)
    created_at = models.DateTimeField(_("created on"), auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    def clean(self):
        from django.core.exceptions import ValidationError
        # Superusers are exempt — they don't belong to a specific location
        if not self.is_superuser and not self.dpu_id and not self.region_id and not self.unit_id:
            raise ValidationError(
                "At least one of DPU, Region, or Unit must be assigned to the user."
            )

    def __str__(self):
        return f"{self.email} - {self.get_full_name()}"
    
    
class LoginSlideshowImage(models.Model):
    """Images displayed in the login page background slideshow."""
    
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    image       = models.ImageField(upload_to='slideshow/')   # stored in Cloudinary
    caption     = models.CharField(max_length=200, blank=True)
    order       = models.PositiveIntegerField(default=0, help_text="Display order (lower = first)")
    is_active   = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'uploaded_at']
        verbose_name        = 'Login Slideshow Image'
        verbose_name_plural = 'Login Slideshow Images'

    def __str__(self):
        return f"Slide {self.order} – {self.caption or self.image.name}"