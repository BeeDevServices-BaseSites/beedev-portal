from userApp.models import User


def _allowed_users(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.CLIENT}