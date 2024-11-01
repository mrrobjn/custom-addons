from odoo import models, fields


class MeetingRoom(models.Model):
    _name = "meeting.room"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Meeting room"


    name = fields.Char(string="Room's name", required=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)
