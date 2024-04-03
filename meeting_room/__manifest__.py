# -*- coding: utf-8 -*-
{
    "name": "Meeting Room Management",
    "summary": """
      Meeting Room Management system""",
    "description": """
        Meeting Room Management
    """,
    "author": "Dung Vo Truong",
    "website": "http://www.yourcompany.com",
    "category": "Uncategorized",
    "version": "0.1",
    "depends": ["base"],
    "data": [
        # 'security/ir.model.access.csv',
        "views/room_view.xml",
        "views/schedule_view.xml",
        "views/menu.xml",
    ],
    "sequence": -100,
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
