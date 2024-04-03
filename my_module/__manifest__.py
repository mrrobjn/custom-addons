# -*- coding: utf-8 -*-
{
    "name": "my_module",
    "summary": """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",
    "description": """
        Long description of module's purpose
    """,
    "author": "My Company",
    "website": "http://www.yourcompany.com",
    "category": "Uncategorized",
    "version": "0.1",
    "depends": ["base"],
    "data": [
        "security/player_security.xml",
        "security/ir.model.access.csv",
        "views/player_views.xml",
    ],
    "application": True,
    "license": "LGPL-3",
}
