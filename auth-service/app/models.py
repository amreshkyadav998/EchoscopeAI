"""Auth-service models — re-exported from the central echoscope_db package.

The schema's single source of truth is the `db/` package (echoscope_db). This
shim keeps existing imports (`from app.models import User, Role, ...`) working.
Migrations live in `db/alembic`, not here.
"""

from echoscope_db.models import Base, Organization, Plan, Role, User

__all__ = ["Base", "Plan", "Role", "Organization", "User"]
