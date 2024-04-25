# -*- coding: utf-8 -*-
{
    "name": "Meeting Room Management",
    "summary": """
      Meeting Room Management system""",
    "description": """
        Meeting Room Management
    """,
    "author": "Duy Huynh Gia",
    "website": "http://www.yourcompany.com",
    "category": "Uncategorized",
    "version": "0.1",
    "depends": ["mail","calendar"],
    "assets": {
        "web.assets_backend": [
            "meeting_room/static/src/css/meeting_room.css",
            "meeting_room/static/src/js/msm.js",
            "meeting_room/static/src/xml/delete_event.xml"
        ],
        'web.assets_qweb': [
            'meeting_room/static/src/xml/delete_event.xml'
        ],
    },
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
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
