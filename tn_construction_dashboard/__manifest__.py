{
    "name": "TN Construction Dashboard",
    "version": "18.0.1.0.0",
    "category": "Project",
    "summary": "Modern construction command center with bilingual dashboard.",
    "description": """
TN Construction Dashboard
=========================
A modern Construction application dashboard for projects, BOQ budgets,
procurement, execution, tasks, operations, contracts, and quality checks.
""",
    "author": "TN",
    "license": "LGPL-3",
    "application": True,
    "depends": [
        "web",
        "project",
        "purchase",
        "tn_construction_boq",
    ],
    "data": [
        "views/backend_assets.xml",
        "views/construction_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "tn_construction_dashboard/static/src/components/construction_dashboard/construction_dashboard.js",
            "tn_construction_dashboard/static/src/components/construction_dashboard/construction_dashboard.xml",
            "tn_construction_dashboard/static/src/components/construction_dashboard/construction_dashboard.scss",
        ],
    },
    "installable": True,
}
