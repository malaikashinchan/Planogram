"""
G5–G11: AI Chat Endpoint
Role is derived from the authenticated backend user, NOT from the frontend request.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict, Any, Optional
from backend.app.auth.dependencies import get_current_user
from backend.app.models.user import User
from pydantic import BaseModel, Field
from litellm import completion
from backend.app.core.config import settings
import os
import traceback
import json

router = APIRouter()


class ChatContext(BaseModel):
    page: Optional[str] = None
    route: Optional[str] = None

    audit_id: Optional[str] = None
    store_id: Optional[str] = None
    planogram_id: Optional[str] = None
    product_id: Optional[str] = None
    review_id: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = Field(default_factory=list)
    context: Optional[ChatContext] = None


def _build_system_prompt(role_names: str, ctx: Optional[ChatContext]) -> str:
    """
    Build the system prompt with:
    - Backend-derived role (G5)
    - Context awareness
    - Tool usage instructions (G6–G11)
    """

    is_manager = any(r in role_names.upper() for r in ["MANAGER", "ADMIN"])
    is_employee = "EMPLOYEE" in role_names.upper()

    # Role-specific capability description
    if is_manager:
        role_description = """You are speaking to a MANAGER.
Managers can:
- View all stores, products, planograms, audits, reviews, and staff/employees
- Add new employees via the Staff page (+ Add Employee button at /manager/employees)
- Deactivate existing employees from the Staff page (Deactivate button per employee)
- Delete employees from the Staff page (Delete button per employee)
- See compliance analytics, violation breakdowns, and trends
- Review ML recognition corrections (Human Reviews)
- Understand the ML model lifecycle and training status
- Navigate to any manager page

STAFF PAGE (/manager/employees) capabilities:
- Lists all employees in the organization with name, email, role, status, last login
- "+ Add Employee" button: invite/create a new employee account
- "Deactivate" button: disable an employee's access without deleting
- "Delete" button: permanently remove an employee

IMPORTANT: When asked about adding employees, deactivating staff, or managing team members,
ALWAYS confirm that this IS supported on the Staff page and navigate there if not already there."""
    elif is_employee:
        role_description = """You are speaking to an EMPLOYEE.
Employees can:
- Start a new shelf audit (capture a photo)
- View their own audit results and compliance scores
- Navigate to: Home (/employee), New Audit (/employee/audit/new)

Employees CANNOT:
- View store compliance overviews
- See other employees' audits
- Access Human Reviews, ML model status, or analytics
- Navigate to any manager page
- Manage products, planograms, or stores

If an employee asks about manager-only features, politely explain this is a manager capability."""
    else:
        role_description = "Unknown role. Provide general help only."

    return f"""You are the Retail Intelligence Assistant, a domain-specific AI copilot built into the Planogram Compliance platform.

AUTHENTICATED USER:
- Role: {role_names}
- Current Page: {ctx.page if ctx else 'Unknown'}
- Route: {ctx.route if ctx else 'Unknown'}
- Audit ID (if on audit page): {ctx.audit_id if ctx and ctx.audit_id else 'None'}
- Store ID: {ctx.store_id if ctx and ctx.store_id else 'None'}
- Planogram ID: {ctx.planogram_id if ctx and ctx.planogram_id else 'None'}
- Review ID: {ctx.review_id if ctx and ctx.review_id else 'None'}

ROLE CONTEXT:
{role_description}

CRITICAL RULES:
1. NEVER invent features. If unsure, use the `search_application_documentation` tool first.
2. If the documentation does not mention a feature, say it is not supported.
3. Keep answers concise, well-formatted, and actionable. Use bullet points.
4. NEVER mention your internal tools by name. Use them silently.
5. For navigation, use `navigate_to_page`. Validate against the user's role.
6. DO NOT assume features exist like user profiles, password changes, batch uploads, or employee self-registration.
7. When explaining violations, always use these precise definitions:
   - MISSING: The planogram expected this product, but it was NOT detected on the shelf.
   - EXTRA: A product was detected that is NOT in the planogram for this position.
   - MISPLACED: The product exists on the shelf but at a DIFFERENT position than the planogram specifies.
   - FACING_MISMATCH: The number of visible facings differs from the planogram's expected count. This does NOT mean the product is facing the wrong direction.
8. When reporting compliance scores to the user, convert decimal values to percentages (e.g., 0.5 → 50%).
9. For managers asking about audits/reviews/analytics, use the appropriate tools to get REAL data. Never guess or make up numbers.
10. For employees, only tools that do NOT require manager role will work. The tool layer enforces this automatically."""


@router.post("/chat")
async def chat_with_assistant(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        is_mock = os.getenv("AI_MOCK_MODE", "false").lower() == "true"
        provider = getattr(settings, "AI_PROVIDER", "openai").lower()
        api_key = getattr(settings, "AI_API_KEY", "")

        model_name = getattr(settings, "AI_MODEL", "gpt-4o-mini")
        if provider != "openai" and not model_name.startswith(provider + "/"):
            model_name = f"{provider}/{model_name}"

        if not api_key:
            if is_mock:
                return {"message": f"{provider.capitalize()} API Key is not configured. Running in offline mock mode!"}
            else:
                raise HTTPException(status_code=500, detail=f"AI Service is not configured (missing API Key for {provider}).")

        ctx = request.context

        # G5: Role is derived from the AUTHENTICATED BACKEND USER, never from the frontend
        role_names = ", ".join([r.name for r in current_user.roles]) if current_user.roles else "Unknown"

        # Build the system prompt
        system_prompt = _build_system_prompt(role_names, ctx)

        # Construct messages
        messages = [{"role": "system", "content": system_prompt}]

        # Add bounded history (last 15 messages)
        recent_history = request.history[-15:] if len(request.history) > 15 else request.history
        for msg in recent_history:
            if msg.role in ["user", "assistant", "system"]:
                messages.append({"role": msg.role, "content": msg.content})

        # Add current message
        messages.append({"role": "user", "content": request.message})

        from backend.app.api.v1.ai_tools import TOOLS, execute_tool
        from backend.app.core.database import SessionLocal

        db = SessionLocal()
        try:
            response = completion(
                model=model_name,
                messages=messages,
                tools=TOOLS,
                api_key=api_key,
                temperature=0.5,
                max_tokens=1500
            )

            response_message = response.choices[0].message

            # Handle tool calls (supports multi-tool in a single turn)
            navigation_route = None
            max_tool_rounds = 3  # Safety limit
            tool_round = 0

            while response_message.tool_calls and tool_round < max_tool_rounds:
                tool_round += 1
                msg_dict = response_message.model_dump() if hasattr(response_message, 'model_dump') else dict(response_message)
                messages.append(msg_dict)

                for tool_call in response_message.tool_calls:
                    args = json.loads(tool_call.function.arguments)

                    # G5: Pass backend-derived role, not frontend role
                    tool_result = execute_tool(
                        tool_call.function.name,
                        args,
                        db,
                        str(current_user.organization_id),
                        role_names,  # Backend-derived role
                        ctx
                    )

                    if tool_result.get("action") == "NAVIGATE":
                        navigation_route = tool_result.get("route")

                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_call.function.name,
                        "content": json.dumps(tool_result)
                    })

                # Follow-up call
                follow_up = completion(
                    model=model_name,
                    messages=messages,
                    tools=TOOLS,
                    api_key=api_key,
                    temperature=0.5,
                    max_tokens=1500
                )
                response_message = follow_up.choices[0].message

            final_content = response_message.content or "I processed your request but have no additional information to share."
            return {"message": final_content, "navigate": navigation_route}

        finally:
            db.close()

    except Exception as e:
        print(f"AI Error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to communicate with the Assistant brain.")
