from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth import decode_access_token

# This tells FastAPI to read a JWT from the Authorization header. HTTP Bearer
# matches this project's JSON login endpoint better than an OAuth2 password
# flow: in Swagger, users log in through /auth/login, copy access_token, and
# paste it into the Authorize dialog.
bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    bearerFormat="JWT",
    auto_error=False,
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency that extracts the current user from a JWT token.

    How it works:
    1. FastAPI reads the "Authorization: Bearer <token>" header
    2. oauth2_scheme extracts the token
    3. We decode the token to get the user ID
    4. We look up the user in the database
    5. If anything fails, we return a 401 Unauthorized error

    Any endpoint that needs authentication adds:
        current_user: User = Depends(get_current_user)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise credentials_exception

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    try:
        parsed_user_id = int(user_id)
    except (ValueError, TypeError):
        raise credentials_exception from None
    user = db.query(User).filter(User.id == parsed_user_id).first()
    if user is None:
        raise credentials_exception

    return user


def require_role(*allowed_roles: str):
    """
    Dependency factory that checks if the current user has the required role.

    Usage in endpoints:
        @router.post("/books/", dependencies=[Depends(require_role("librarian", "admin"))])

    This means: "Only librarians and admins can access this endpoint."

    How it works:
    - It returns a FUNCTION (that's what "factory" means — a function that creates functions)
    - The inner function receives the current user and checks their role
    - If the role doesn't match, it returns a 403 Forbidden error
    """

    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role.value not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return role_checker
