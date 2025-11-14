"""
Authentication views for user registration and login
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    """
    Register a new user
    POST /api/auth/register/
    Body: { "username": "...", "email": "...", "password": "..." }
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # No authentication required

    def post(self, request):
        try:
            username = request.data.get('username', '').strip()
            email = request.data.get('email', '').strip()
            password = request.data.get('password', '')

            if not username or not password:
                return Response(
                    {'error': 'Username and password are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if len(password) < 8:
                return Response(
                    {'error': 'Password must be at least 8 characters long'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if User.objects.filter(username=username).exists():
                return Response(
                    {'error': 'Username already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if email and User.objects.filter(email=email).exists():
                return Response(
                    {'error': 'Email already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = User.objects.create_user(
                username=username,
                email=email or '',
                password=password
            )
            return Response(
                {
                    'message': 'User created successfully',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email
                    }
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': f'Registration failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    """
    Login a user
    POST /api/auth/login/
    Body: { "username": "...", "password": "..." }
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # No authentication required

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return Response(
                {
                    'message': 'Login successful',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email
                    }
                },
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': 'Invalid username or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )


@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    """
    Logout the current user
    POST /api/auth/logout/
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # No authentication required

    def post(self, request):
        logout(request)
        return Response(
            {'message': 'Logout successful'},
            status=status.HTTP_200_OK
        )


class CurrentUserView(APIView):
    """
    Get the current authenticated user
    GET /api/auth/user/
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # Allow checking without auth

    def get(self, request):
        if request.user.is_authenticated:
            return Response(
                {
                    'id': request.user.id,
                    'username': request.user.username,
                    'email': request.user.email
                },
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': 'Not authenticated'},
                status=status.HTTP_401_UNAUTHORIZED
            )

