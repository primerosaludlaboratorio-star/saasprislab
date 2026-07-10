# 6. Role Based Access Control (RBAC) via Decorators

Date: 2026-07-10

## Status

Accepted

## Context

The PRISLAB SaaS platform needs to manage access control across multiple modules (Laboratorio, Farmacia, Consultorio, Financiero). Since tenants (Empresas) share the same infrastructure but have distinct operational roles (DIRECTOR, MEDICO, QUIMICO, CAJERO, RECEPCION, FINANZAS, etc.), a robust yet simple mechanism to enforce authorization at the view level is required.

## Decision

We have decided to centralize RBAC using a custom Django decorator (`@role_required`) located in `core/decorators.py`. 

This decorator:
1. Validates the `user.rol` against a list of allowed roles.
2. Bypasses the check for `is_superuser` and `is_staff` to ensure system administrators are never locked out of critical functions.
3. Automatically responds with `403 Forbidden` (or a JSON error payload for AJAX requests) if the user lacks the proper role.
4. Logs unauthorized access attempts to provide auditability (Governance).

## Consequences

- **Positive:** Authorization logic is removed from inside the view bodies, keeping the views clean and adhering to the Single Responsibility Principle.
- **Positive:** Centralized logging of access denials improves security observability.
- **Negative:** Hardcoding string roles (e.g., `'MEDICO'`, `'ADMIN'`) in view decorators means that introducing new roles might require modifying multiple files if the roles map directly to specific features instead of generic access levels.
