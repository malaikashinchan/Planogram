import asyncio
from fastapi import Request
from backend.app.auth.dependencies import require_roles
from backend.app.models.user import User, Role
class MockRole:
    def __init__(self, name):
        self.name = name
class MockUser:
    def __init__(self, roles):
        self.roles = roles
mock_user = MockUser([MockRole("ADMIN")])

def mock_get_current_user(request, db):
    return mock_user

import backend.app.auth.dependencies as deps
deps.get_current_user = mock_get_current_user

dependency = require_roles("ADMIN", "MANAGER").dependency
try:
    dependency(None, None)
    print("SUCCESS")
except Exception as e:
    print("FAILED", str(e))
