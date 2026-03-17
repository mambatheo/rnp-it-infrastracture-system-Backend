# serializers.py
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'dpu', 'region', 'unit',
            'full_name', 'phone_number', 'role', 'is_active',
            'is_locked', 'locked_until', 'created_at', 'is_staff'
        ]
        read_only_fields = ['id', 'created_at', 'is_locked', 'locked_until']

    def get_full_name(self, obj) -> str:
        return obj.get_full_name()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'dpu', 'region', 'unit',
            'phone_number', 'role', 'password', 'password_confirm'
        ]
        extra_kwargs = {
            'role':   {'required': True},
            # Explicitly mark FK location fields as optional and nullable
            'dpu':    {'required': False, 'allow_null': True},
            'region': {'required': False, 'allow_null': True},
            'unit':   {'required': False, 'allow_null': True},
        }

    def validate_phone_number(self, value):
        if value and len(value) != 10:
            raise serializers.ValidationError("Phone number must be exactly 10 digits.")
        return value

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        # At least one of dpu, region, or unit must be assigned.
        # DRF resolves FK fields to model instances in attrs, so check truthiness directly.
        has_location = bool(attrs.get('dpu')) or bool(attrs.get('region')) or bool(attrs.get('unit'))
        if not has_location:
            raise serializers.ValidationError(
                {"non_field_errors": "At least one of DPU, Region, or Unit must be assigned to the user."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        dpu    = validated_data.pop('dpu', None)
        region = validated_data.pop('region', None)
        unit   = validated_data.pop('unit', None)
        role   = validated_data.pop('role')
        user = User.objects.create_user(
            password=password,
            dpu=dpu,
            region=region,
            unit=unit,
            **validated_data,
        )
        user.role      = role
        user.is_active = False  
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone_number', 'dpu', 'region', 'unit', 'role', 'is_active']


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class AdminSetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return attrs

    def save(self, user):
        validate_password(self.validated_data['new_password'], user)
        user.set_password(self.validated_data['new_password'])
        user.is_first_login = True  
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return attrs

    def save(self):
        user = self.context['request'].user
        validate_password(self.validated_data['new_password'], user)
        user.set_password(self.validated_data['new_password'])
        user.is_first_login = False
        user.save()
        return user