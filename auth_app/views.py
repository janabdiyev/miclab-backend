from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from datetime import datetime, timedelta, timezone
from songs.models import UserProfile
import json


class AuthViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def register(self, request):
        """Register a new user with 5-day free trial"""
        email = request.data.get('email')
        password = request.data.get('password')
        username = request.data.get('username', email.split('@')[0])

        if not email or not password:
            return Response(
                {'detail': 'Email and password required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {'detail': 'Email already registered'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # Create profile with 5-day trial
        now = datetime.now(timezone.utc)
        trial_end = now + timedelta(days=5)
        
        profile = UserProfile.objects.create(
            user=user,
            subscription_type='free',
            trial_start_date=now,
            trial_end_date=trial_end
        )

        # Create token
        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            'user_id': user.id,
            'email': user.email,
            'token': token.key,
            'trial_end_date': profile.trial_end_date.isoformat(),
            'subscription_type': profile.subscription_type
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def login(self, request):
        """Login user and return token"""
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'detail': 'Email and password required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(email=email).first()
        if not user or not user.check_password(password):
            return Response(
                {'detail': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token, _ = Token.objects.get_or_create(user=user)
        profile = UserProfile.objects.get(user=user)

        return Response({
            'user_id': user.id,
            'email': user.email,
            'token': token.key,
            'subscription_type': profile.subscription_type,
            'trial_end_date': profile.trial_end_date.isoformat() if profile.trial_end_date else None,
            'subscription_end_date': profile.subscription_end_date.isoformat() if profile.subscription_end_date else None
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Get current user profile"""
        profile = UserProfile.objects.get(user=request.user)
        
        # Check if trial expired
        now = datetime.now(timezone.utc)
        if profile.subscription_type == 'free' and profile.trial_end_date and profile.trial_end_date < now:
            profile.subscription_type = 'expired'
            profile.save()

        return Response({
            'user_id': request.user.id,
            'email': request.user.email,
            'username': request.user.username,
            'subscription_type': profile.subscription_type,
            'trial_start_date': profile.trial_start_date.isoformat() if profile.trial_start_date else None,
            'trial_end_date': profile.trial_end_date.isoformat() if profile.trial_end_date else None,
            'subscription_start_date': profile.subscription_start_date.isoformat() if profile.subscription_start_date else None,
            'subscription_end_date': profile.subscription_end_date.isoformat() if profile.subscription_end_date else None
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def purchase(self, request):
        """Handle IAP purchase (iOS/Android)"""
        product_id = request.data.get('product_id')
        receipt = request.data.get('receipt')
        platform = request.data.get('platform')  # 'ios' or 'android'

        if not product_id or not receipt:
            return Response(
                {'detail': 'product_id and receipt required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Map product IDs to subscription types
        product_mapping = {
            'com.miclab.premium.monthly': 'premium_monthly',
            'com.miclab.premium.yearly': 'premium_yearly',
        }

        subscription_type = product_mapping.get(product_id)
        if not subscription_type:
            return Response(
                {'detail': 'Invalid product_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # TODO: Verify receipt with Apple/Google
        # For now, we'll accept it (implement proper verification in production)

        # Update user subscription
        profile = UserProfile.objects.get(user=request.user)
        now = datetime.now(timezone.utc)

        profile.subscription_type = subscription_type
        profile.subscription_start_date = now

        if subscription_type == 'premium_monthly':
            profile.subscription_end_date = now + timedelta(days=30)
        elif subscription_type == 'premium_yearly':
            profile.subscription_end_date = now + timedelta(days=365)

        profile.save()

        return Response({
            'subscription_type': profile.subscription_type,
            'subscription_end_date': profile.subscription_end_date.isoformat()
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def check_access(self, request):
        """Check if user has access (premium or valid trial)"""
        profile = UserProfile.objects.get(user=request.user)
        now = datetime.now(timezone.utc)

        # Premium users
        if profile.subscription_type in ['premium_monthly', 'premium_yearly']:
            if profile.subscription_end_date and profile.subscription_end_date > now:
                return Response({'access': True, 'reason': 'Premium subscriber'})

        # Free trial users
        if profile.subscription_type == 'free' and profile.trial_end_date:
            if profile.trial_end_date > now:
                days_left = (profile.trial_end_date - now).days
                return Response({'access': True, 'reason': f'Trial ({days_left} days left)'})
            else:
                return Response({'access': False, 'reason': 'Trial expired'}, status=status.HTTP_403_FORBIDDEN)

        return Response({'access': False, 'reason': 'No active subscription'}, status=status.HTTP_403_FORBIDDEN)
