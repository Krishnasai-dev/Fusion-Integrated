"""What the server tells the shell about this module (ADR-0010)."""
MODULE = {
    "code": "elm", "label": "Employee Leave", "icon": "FaCalendarCheck",
    "base_path": "/elm", "nav_section": "Employee", "sort_order": 40,
    "status": "planned",
}

NAV_ITEMS: list[dict] = []

PERMISSIONS = [
    ("elm.leave_request.apply", "Apply for and withdraw own leave"),
    ("elm.leave_request.respond", "Accept or decline a substitute nomination"),
    ("elm.leave_request.view", "View leave requests of others"),
    ("elm.leave_request.review", "Unit Head review of leave"),
    ("elm.leave_request.process", "Establishment routing of leave"),
    ("elm.leave_request.sanction", "Final sanction of leave"),
    ("elm.leave_request.self_sanction", "Director self-sanction path"),
    ("elm.vacation_leave.apply", "Faculty vacation leave entitlement"),
]

SYSTEM_PERMISSIONS: list[str] = []

_EMPLOYEE = ["elm.leave_request.apply", "elm.leave_request.respond"]

ROLE_GRANTS = {
    "student": [],
    "leave_admin": [*_EMPLOYEE, "elm.leave_request.view"],
    "faculty": [*_EMPLOYEE, "elm.vacation_leave.apply"],
    "staff": _EMPLOYEE,
    "hod": [*_EMPLOYEE, "elm.vacation_leave.apply", "elm.leave_request.review"],
    "dean": [*_EMPLOYEE, "elm.leave_request.sanction"],
    "registrar": [*_EMPLOYEE, "elm.leave_request.sanction", "elm.leave_request.process"],
    "director": [*_EMPLOYEE, "elm.leave_request.sanction", "elm.leave_request.self_sanction"],
}
