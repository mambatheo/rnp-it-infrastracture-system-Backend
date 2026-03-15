import uuid
from django.db import models
from django.utils.translation import gettext as _
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.validators import MaxLengthValidator, MinLengthValidator


class UserManager(BaseUserManager):

    def create_user(self, email, first_name, last_name, phone_number=None, password=None, **extra_fields):
        
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            **extra_fields,
        )
        must_change_password = models.Boolean(default=True)
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
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    TECHNICIAN = 'TECHNICIAN'
    IT_STAFF = 'IT STAFF'
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

    def __str__(self):
        return f"{self.email} - {self.get_full_name()}"