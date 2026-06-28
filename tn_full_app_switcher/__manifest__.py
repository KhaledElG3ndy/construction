{
    "name": "TN Full App Switcher",
    "version": "18.0.1.0.0",
    "category": "Tools",
    "summary": "Replace the navbar apps dropdown with a full-screen app grid.",
    "author": "TN",
    "license": "LGPL-3",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "tn_full_app_switcher/static/src/app_switcher/full_app_switcher.js",
            "tn_full_app_switcher/static/src/app_switcher/full_app_switcher.xml",
            "tn_full_app_switcher/static/src/app_switcher/full_app_switcher.scss",
        ],
    },
    "installable": True,
    "application": False,
}
