from datetime import datetime, timedelta, timezone

import jwt

from app.exceptions import InvalidCredentialsError, AccountBlockedError, InvalidTokenError


class AuthService:
    def __init__(self, account_repo, secret_key: str, algorithm: str = "HS256", token_ttl_minutes: int = 30):
        self.account_repo = account_repo
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_ttl = timedelta(minutes=token_ttl_minutes)

    async def authenticate(self, login: str, password: str) -> str:
        account = await self.account_repo.get_by_login_and_password(login, password)
        if account is None:
            raise InvalidCredentialsError("Invalid login or password")
        if account.is_blocked:
            raise AccountBlockedError("Account is blocked")
        return self.create_token(account.id, account.login)

    def create_token(self, account_id: int, login: str) -> str:
        payload = {
            "sub": str(account_id),
            "login": login,
            "exp": datetime.now(timezone.utc) + self.token_ttl,
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            payload["sub"] = int(payload["sub"])
            return payload
        except jwt.ExpiredSignatureError:
            raise InvalidTokenError("Token has expired")
        except jwt.InvalidTokenError:
            raise InvalidTokenError("Invalid token")
