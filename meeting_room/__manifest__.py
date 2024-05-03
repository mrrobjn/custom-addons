# -*- coding: utf-8 -*-
{
    "name": "Meeting Room Management",
    "summary": """
      Meeting Room Management system""",
    "description": """
        Meeting Room Management
    """,
    "author": "Intern FullStack",
    "website": "http://www.yourcompany.com",
    "category": "Uncategorized",
    "version": "0.1",
    "depends": ["mail","calendar"],
    "assets": {
        "web.assets_backend": [
            "meeting_room/static/src/css/meeting_room.css",
            "meeting_room/static/js/schedule.js",
            # "meeting_room/static/js/calendar_controller.js",
        ],
        'web.assets_qweb':[
            # "meeting_room/static/xml/test.xml",
            'meeting_room/static/xml/delete_event.xml',
            # 'meeting_room/static/js/calendar_rendder.js'
        ],
    },
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/room_view.xml",
        "views/schedule_view.xml",
        "views/menu.xml",
        'data/mail_template.xml',
        
    ],
    "sequence": -100,
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
