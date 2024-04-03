from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta


class MeetingRoom(models.Model):
    _name = "meeting.schedule"
    _description = "Meeting schedule"

    meeting_subject = fields.Char(string="Meeting subject", required=True)
    booking_date = fields.Datetime(
        string="Booking Date", default=fields.Date.context_today
    )
    duration = fields.Integer(string="Duration(hours)", default=1, required=True)
    end_date = fields.Datetime(
        string="End Date", compute="_compute_end_date", store=True
    )
    room_id = fields.Many2one("meeting.room", string="Room", ondelete="cascade")

    @api.constrains("duration")
    def _check_duration(self):
        for appointment in self:
            if appointment.duration < 1:
                raise ValidationError("Duration must be at least 1 hour")

    @api.depends("booking_date", "duration")
    def _compute_end_date(self):
        for appointment in self:
            if appointment.booking_date and appointment.duration:
                start_date = fields.Datetime.from_string(appointment.booking_date)
                end_date = start_date + timedelta(hours=appointment.duration)
                appointment.end_date = end_date
