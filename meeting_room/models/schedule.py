from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta, datetime
from pytz import timezone


class MeetingSchedule(models.Model):
    _name = "meeting.schedule"
    _description = "Meeting schedule"
    _order = "start_date asc"

    name = fields.Char(
        string="Room name", compute="_compute_meeting_name", required=True
    )
    meeting_subject = fields.Char(string="Meeting subject", required=True)
    description = fields.Text(string="Description")
    meeting_type = fields.Selection(
        [
            ("daily", "Daily Meeting"),
            ("weekly", "Weekly Meeting"),
        ],
        string="Meeting type",
        default="daily",
        required=True,
    )
    start_daily = fields.Date(string="Start date", default=fields.Date.context_today)
    end_daily = fields.Date(string="End date", default=fields.Date.context_today)

    start_date = fields.Datetime(
        string="Start datetime",
        default=fields.Date.context_today,
    )

    end_date = fields.Datetime(string="End datetime", default=fields.Date.context_today)
    hours_selection = [
        (str(hour).zfill(2), "{:02d}:00".format(hour)) for hour in range(24)
    ]
    start_time = fields.Selection(
        selection=hours_selection,
        string="Start time",
    )
    end_time = fields.Selection(
        selection=hours_selection,
        string="End time",
    )
    duration = fields.Integer(
        string="Duration(hour)",
        compute="_compute_duration",
        store=True,
    )

    room_id = fields.Many2one(
        "meeting.room", string="Room name", ondelete="cascade", required=True
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company name",
        required=True,
        default=lambda self: self.env.company,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Created by",
        required=True,
        default=lambda self: self.env.user,
    )
    day = fields.Char(
        "Day",
        compute="_compute_date_start",
    )
    month = fields.Char(
        "Month and Year",
        compute="_compute_date_start",
    )
    time = fields.Char(
        "Time",
        compute="_compute_date_start",
    )
    repeat_weekly = fields.Integer(string="Repeat Weekly", default=0)
    parent_ids = fields.Many2one(
        "meeting.schedule",
        string="Parent Schedule",
        ondelete="cascade",
        index=True,
        help="Parent schedule for repeated meetings.",
    )
    is_parent = fields.Boolean(string="Parent meeting", default=True)

    # Computed Fields
    @api.depends("name")
    def _compute_meeting_name(self):
        for record in self:
            record.name = record.room_id.name

    @api.depends("start_date")
    def _compute_date_start(self):
        for record in self:
            if record.start_date:
                user_tz = self.env.user.tz or "UTC"
                local_tz = timezone(user_tz)
                date_obj = fields.Datetime.from_string(record.start_date).astimezone(
                    local_tz
                )
                record.day = date_obj.strftime("%-d")
                record.month = date_obj.strftime("%b %Y")
                record.time = date_obj.strftime("%H:%M")

    @api.depends("start_time", "end_time")
    def _compute_duration(self):
        for record in self:
            if record.start_time and record.start_time:
                duration = int(record.end_time) - int(record.start_time)
                record.duration = duration

    # Constraints
    @api.constrains("start_date", "end_date")
    def _check_is_same_date(self):
        for schedule in self:
            if (
                schedule.meeting_type != "daily"
                and schedule.start_date.date() != schedule.end_date.date()
            ):
                raise ValidationError("Start and end dates must be the same day")

    @api.constrains("duration")
    def _check_date(self):
        for schedule in self:
            if schedule.duration < 1:
                raise ValidationError("Duration must be at least 1 hour")

    @api.constrains("repeat_weekly")
    def _check_max_value(self):
        for record in self:
            if record.repeat_weekly > 10:
                raise ValidationError("Maximum weekLy meeting allowed is 10.")

    @api.constrains("start_date", "duration", "room_id")
    def _check_room_availability(self):
        for schedule in self:
            if schedule.start_date and schedule.duration and schedule.room_id:
                start_datetime = fields.Datetime.from_string(schedule.start_date)
                end_datetime = start_datetime + timedelta(hours=schedule.duration)

                conflicting_bookings = self.env["meeting.schedule"].search(
                    [
                        ("room_id", "=", schedule.room_id.id),
                        ("id", "!=", schedule.id),
                        ("start_date", "<", end_datetime),
                        ("end_date", ">", start_datetime),
                    ]
                )

                if conflicting_bookings:
                    raise ValidationError(
                        "The room is already booked for this time period."
                    )

    @api.onchange("start_date")
    def _onchange_start_date(self):
        for schedule in self:
            if schedule.start_date:
                adjusted_start_date = schedule.start_date + timedelta(hours=7)
                schedule.start_daily = fields.Date.to_string(adjusted_start_date.date())
                schedule.start_time = adjusted_start_date.strftime("%H")

    @api.onchange("end_date")
    def _onchange_end_date(self):
        for schedule in self:
            if schedule.end_date:
                adjusted_end_date = schedule.end_date + timedelta(hours=7)
                schedule.end_daily = fields.Date.to_string(adjusted_end_date.date())
                schedule.end_time = adjusted_end_date.strftime("%H")

    @api.onchange("start_daily", "start_time")
    def _onchange_date_start_time(self):
        for schedule in self:
            if schedule.start_daily and schedule.start_time:
                time_obj = datetime.strptime(schedule.start_time, "%H").time()
                date_obj = fields.Date.from_string(schedule.start_daily)
                combined_datetime = datetime.combine(date_obj, time_obj)
                adjusted_datetime = combined_datetime - timedelta(hours=7)
                schedule.start_date = adjusted_datetime

    @api.onchange("end_daily", "end_time")
    def _onchange_date_end_time(self):
        for schedule in self:
            if schedule.end_daily and schedule.end_time:
                time_obj = datetime.strptime(schedule.end_time, "%H").time()
                date_obj = fields.Date.from_string(schedule.end_daily)
                combined_datetime = datetime.combine(date_obj, time_obj)
                adjusted_datetime = combined_datetime - timedelta(hours=7)
                schedule.end_date = adjusted_datetime

    # Business Logic Methods
    def create_daily(self):
        start_datetime = fields.Datetime.from_string(self.start_date)
        end_datetime = fields.Datetime.from_string(self.end_date)
        self.write(
            {
                "end_date": fields.Datetime.to_string(
                    start_datetime + timedelta(hours=self.duration)
                ),
            }
        )
        delta_days = (end_datetime - start_datetime).days

        for day in range(delta_days + 1):
            meeting_date = start_datetime + timedelta(days=day)
            if meeting_date == self.start_date:
                continue
            else:
                self.env["meeting.schedule"].create(
                    {
                        "name": self.name,
                        "meeting_subject": self.meeting_subject,
                        "description": self.description,
                        "meeting_type": self.meeting_type,
                        "start_date": fields.Datetime.to_string(meeting_date),
                        "end_date": fields.Datetime.to_string(
                            meeting_date + timedelta(hours=self.duration)
                        ),
                        "start_time": self.start_time,
                        "end_time": self.end_time,
                        "duration": self.duration,
                        "room_id": self.room_id.id,
                        "company_id": self.company_id.id,
                        "user_id": self.user_id.id,
                        "parent_ids": self.id,
                        "is_parent": False,
                    }
                )

    def create_weekly(self):
        schedules_to_create = []
        for schedule in self:
            for i in range(schedule.repeat_weekly):
                start_date = fields.Datetime.from_string(schedule.start_date)
                new_start_date = start_date + timedelta(weeks=i + 1)
                new_end_date = fields.Datetime.from_string(
                    schedule.end_date
                ) + timedelta(weeks=i + 1)

                new_schedule = {
                    "name": schedule.room_id.name,
                    "meeting_subject": schedule.meeting_subject,
                    "description": schedule.description,
                    "start_date": new_start_date,
                    "end_date": new_end_date,
                    "start_time": self.start_time,
                    "end_time": self.end_time,
                    "room_id": schedule.room_id.id,
                    "company_id": schedule.company_id.id,
                    "duration": self.duration,
                    "user_id": schedule.user_id.id,
                    "repeat_weekly": 0,
                    "parent_ids": schedule.id,
                    "is_parent": False,
                }
                schedules_to_create.append(new_schedule)

        self.env["meeting.schedule"].create(schedules_to_create)

    # CRUD Methods
    @api.model
    def create(self, vals):
        meeting_schedule = super(MeetingSchedule, self).create(vals)

        start_date = vals.get("start_date")

        if not self.env.user.has_group("meeting_room.group_meeting_room_hr"):
            if isinstance(start_date, datetime):
                if start_date < fields.Datetime.now():
                    raise ValidationError("Start date cannot be in the past")
            else:
                if (
                    datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
                    < fields.Datetime.now()
                ):
                    raise ValidationError("Start date cannot be in the past")

        meeting_type = vals.get("meeting_type")
        if meeting_type == "daily":
            meeting_schedule.create_daily()
        elif meeting_type == "weekly":
            meeting_schedule.create_weekly()
        return meeting_schedule

    def write(self, vals):
        if self.start_date < fields.Datetime.now() and not self.env.user.has_group(
            "meeting_room.group_meeting_room_hr"
        ):
            raise ValidationError("Cannot edit ongoing or finished meetings")
        return super(MeetingSchedule, self).write(vals)

    def unlink(self):
        if self.start_date < fields.Datetime.now() and not self.env.user.has_group(
            "meeting_room.group_meeting_room_hr"
        ):
            raise ValidationError("Cannot delete ongoing or finished meetings.")
        return super(MeetingSchedule, self).unlink()
