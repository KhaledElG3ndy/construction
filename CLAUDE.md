# CLAUDE.md — Construction Control Tower (Odoo 18)

## What this project is
Custom Odoo 18 modules that turn Odoo into a construction governance ERP for a Grade-A
contractor in Saudi Arabia. The modules are a reusable PRODUCT: no client-specific
hardcoding, everything config-driven, so the same code resells to future KSA clients.

## Environment
- Odoo 18 Community, source at `/opt/odoo18/odoo`
- Python venv at `/opt/odoo18/venv`
- Custom modules live HERE: `/opt/odoo18/custom-addons` (this directory)
- Config: `/etc/odoo18/odoo18.conf`  (addons_path already includes this folder)
- Service: `odoo18` (systemd).  DB user: `odoo18`
- Logs: `/var/log/odoo18/odoo18.log`

## How to test a change (use this loop)
1. Restart Odoo:           `sudo systemctl restart odoo18`
2. Update a module:        `sudo -u odoo18 /opt/odoo18/venv/bin/python3 /opt/odoo18/odoo/odoo-bin -c /etc/odoo18/odoo18.conf -d <DB> -u <module> --stop-after-init`
3. Watch the log:          `tail -n 100 -f /var/log/odoo18/odoo18.log`
4. Confirm "module loaded" / no traceback before declaring done.
Never edit core Odoo under /opt/odoo18/odoo. Only write modules in this folder.

## Non-negotiable architecture rules (from the CTO blueprint)
1. **Edition-portable.** Code MUST run on both Community and Enterprise. Do NOT depend on
   Enterprise-only modules (no `account_accountant`, `web_studio`, `sale_subscription`, etc.).
   Extend Community base apps only: project, account, purchase, stock, hr, mrp.
2. **Module prefix is `tn_`** (our product brand), never the client's name.
3. **Small independent addons**, each with its own manifest, security, views, tests.
   Build order: tn_construction_base → tn_construction_boq → tn_boq_budget_control →
   tn_construction_dpr → tn_construction_procurement → (phase 2 modules later).
4. **Server-side enforcement.** The BOQ hard-stop must validate in Python on
   create/write/confirm (raise UserError), NOT only in the UI. UI checks are sugar.
5. **Analytic accounting is the cost backbone.** Every project = analytic account;
   every cost ties to project + cost code + BOQ line.
6. **Bilingual EN/AR with RTL** considered from the start (translatable strings, no
   hardcoded English in logic).
7. **No fake performance promises** in comments or docs. Behaviour, not benchmarks.

## The crown-jewel feature: BOQ hard-stop
When a material/PO request quantity would exceed the approved remaining BOQ quantity for a
line, BLOCK it (raise UserError) showing remaining qty. Override ONLY via an approved
Variation Order or Budget Revision — never a plain "approve anyway".
Track per BOQ line: requested → approved → ordered → received → issued → consumed.
Remaining = approved − committed.

## Odoo 18 conventions to follow
- Manifests: `'license': 'LGPL-3'`, correct `depends`, `'application': True` for top-level.
- Views: Odoo 18 uses `<list>` not `<tree>`. Use modern view syntax.
- Always add `ir.model.access.csv` security for every new model, plus record rules where
  multi-project access control matters.
- Use `account.analytic.account` / `account.analytic.line` for cost tracking.
- Prefer extending existing models (`_inherit`) over duplicating.

## Working style I want
- Before building a module, show me the file tree you plan, then build.
- Build ONE module at a time, load it, confirm no traceback, then move on.
- After each module, give me a one-line manual test I can click through in the UI.
- Keep demo data realistic for a Saudi roads/building contractor (SAR currency).
