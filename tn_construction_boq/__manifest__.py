{
    'name': 'TN Construction - BOQ Budget Control',
    'version': '18.0.1.0.0',
    'category': 'Project',
    'summary': 'Bill of Quantities budget control with a hard-stop on '
               'over-budget procurement.',
    'description': """
TN Construction - BOQ Budget Control
====================================
Adds a Bill of Quantities (BOQ) per project and enforces a server-side
hard-stop: a purchase order that would commit more quantity than the
approved BOQ quantity for a product is blocked (UserError) unless an
approved Variation Order override is set on the PO.

Edition-portable: depends only on Community apps (project, purchase).
""",
    'author': 'TN',
    'license': 'LGPL-3',
    'application': False,
    'depends': [
        'project',
        'product',
        'purchase',
        'stock',
        'hr',
    ],
    'data': [
        'data/ir_sequence.xml',
        'data/construction_configuration_data.xml',
        'security/ir.model.access.csv',
        'views/tn_boq_line_views.xml',
        'views/project_project_views.xml',
        'views/configuration_views.xml',
        'views/subcontract_views.xml',
        'views/quality_check_views.xml',
        'views/execution_views.xml',
        'views/task_views.xml',
        'views/operations_views.xml',
        'views/purchase_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tn_construction_boq/static/src/scss/construction_project.scss',
        ],
    },
    'installable': True,
}
