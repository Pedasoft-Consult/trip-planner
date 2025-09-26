# apps/core/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed


class CookiesOrHeaderJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication:
    - First checks 'access_token' in cookies
    - If not found, falls back to 'Authorization: Bearer <token>' header
    """

    def authenticate(self, request):
        # 1. Check cookies
        access_token = request.COOKIES.get("access_token")
        if access_token:
            try:
                validated_token = self.get_validated_token(access_token)
                user = self.get_user(validated_token)
                return (user, validated_token)
            except AuthenticationFailed:
                return None  # invalid/expired token in cookie → fall back to header

        # 2. Fallback to default header-based JWT auth
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)

        return (user, validated_token)
