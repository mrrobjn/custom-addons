from odoo import models, fields


class MeetingRoom(models.Model):
    _name = "meeting.room"
    _description = "Meeting room"

    name = fields.Char(string="Room name", required=True)
    active = fields.Boolean(string="Active", default=True)
