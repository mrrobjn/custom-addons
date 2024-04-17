from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta, datetime
from pytz import timezone
from dateutil import parser


class MeetingSchedule(models.Model):
    _name = "meeting.schedule"
    _description = "Meeting schedule"
    _order = "start_date asc"

    name = fields.Char(
        string="Thumbnail", compute="_compute_meeting_name", required=True
    )
    meeting_subject = fields.Char(string="Meeting subject", required=True)
    description = fields.Text(string="Description")
    meeting_type = fields.Selection(
        string="Meeting type",
        default="normal",
        required=True,
        selection=[
            ("normal", "Normal Meeting"),
            ("daily", "Daily Meeting"),
            ("weekly", "Weekly Meeting"),
        ],
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
    repeat_weekly = fields.Integer(string="Repeat Weekly", default=1)
    parent_ids = fields.Many2one(
        "meeting.schedule",
        string="Parent Meeting",
        ondelete="cascade",
        index=True,
        help="Parent schedule for repeated meetings.",
    )
    is_parent = fields.Boolean(string="Parent Schedule", default=True)

    monday = fields.Boolean(string="Monday", default=True)
    tuesday = fields.Boolean(string="Tuesday", default=True)
    wednesday = fields.Boolean(string="Wednesday", default=True)
    thursday = fields.Boolean(string="Thursday", default=True)
    friday = fields.Boolean(string="Friday", default=True)
    saturday = fields.Boolean(string="Saturday", default=False)
    sunday = fields.Boolean(string="Sunday", default=False)

    # Computed Fields
    @api.depends("name")
    def _compute_meeting_name(self):
        for record in self:
            if record.is_parent:
                record.name = f"{record.room_id.name} - {record.user_id.name} - Parent Meeting"
            else:
                record.name = f"{record.room_id.name} - {record.user_id.name}"


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
            if record.start_time and record.end_time:
                duration = int(record.end_time) - int(record.start_time)
                record.duration = duration

    # Constraints
    @api.constrains("start_date", "end_date")
    def _check_date(self):
        for schedule in self:
            if (
                schedule.meeting_type == "normal"
                and schedule.start_date.date() != schedule.end_date.date()
            ):
                raise ValidationError("Start and end dates must be the same day")
            if (
                schedule.meeting_type == "daily"
                and schedule.start_date.date() > schedule.end_date.date()
            ):
                raise ValidationError("Start date can not bigger than end date")
            if (
                schedule.meeting_type == "weekly"
                and schedule.start_date.date() != schedule.end_date.date()
            ):
                raise ValidationError("Start and end dates must be the same day")

    # @api.constrains("duration")
    # def _check_date(self):
    #     for schedule in self:
    #         if schedule.duration < 1:
    #             raise ValidationError("Duration must be at least 1 hour")

    @api.constrains("start_date")
    def _check_start_date(self):
        for record in self:
            start_datetime = fields.Datetime.from_string(record.start_date)
            weekday_mapping = {
                0: ("Monday", record.monday),
                1: ("Tuesday", record.tuesday),
                2: ("Wednesday", record.wednesday),
                3: ("Thursday", record.thursday),
                4: ("Friday", record.friday),
                5: ("Saturday", record.saturday),
                6: ("Sunday", record.sunday),
            }
            weekday_name, allowed = weekday_mapping.get(start_datetime.weekday())

            if not allowed and record.meeting_type != "normal":
                raise ValidationError(
                    f"Start date cannot be scheduled on {weekday_name}."
                )

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

                if conflicting_bookings := self.env["meeting.schedule"].search(
                    [
                        ("room_id", "=", schedule.room_id.id),
                        ("id", "!=", schedule.id),
                        ("start_date", "<", end_datetime),
                        ("end_date", ">", start_datetime),
                    ]
                ):
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
    def action_delete_many(self):
            return {
                "name": "Select action",
                "res_model": "transient.model",
                "view_mode": "form",
                "target": "new",
                "type": "ir.actions.act_window",
            }

    def create_daily(self):
        start_datetime = fields.Datetime.from_string(self.start_date)
        end_datetime = fields.Datetime.from_string(self.end_date)

        end_date = start_datetime + timedelta(hours=self.duration)
        self.write(
            {
                "end_date": fields.Datetime.to_string(end_date),
                "end_daily": self.start_daily,
            }
        )
        weekday_attributes = [
            self.monday,
            self.tuesday,
            self.wednesday,
            self.thursday,
            self.friday,
            self.saturday,
            self.sunday,
        ]
        weekday_mapping = dict(zip(range(7), weekday_attributes))

        meeting_dates = [
            start_datetime + timedelta(days=day)
            for day in range(1, (end_datetime - start_datetime).days + 1)
        ]

        for meeting_date in meeting_dates:
            if weekday_mapping.get(meeting_date.weekday(), False):
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
            start_date = fields.Datetime.from_string(schedule.start_date)
            end_date = fields.Datetime.from_string(schedule.end_date)
            weekdays_to_exclude = [
                not getattr(schedule, day)
                for day in [
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                ]
            ]
            for i in range(schedule.repeat_weekly):
                new_schedules = []
                for day_offset in range(7):
                    current_date = start_date + timedelta(weeks=i, days=day_offset)
                    if (
                        not weekdays_to_exclude[current_date.weekday()]
                        and current_date != start_date
                    ):
                        new_schedules.append(
                            {
                                "name": schedule.room_id.name,
                                "meeting_subject": schedule.meeting_subject,
                                "description": schedule.description,
                                "start_date": current_date,
                                "end_date": current_date
                                + timedelta(hours=self.duration),
                                "start_time": schedule.start_time,
                                "meeting_type": schedule.meeting_type,
                                "end_time": schedule.end_time,
                                "room_id": schedule.room_id.id,
                                "company_id": schedule.company_id.id,
                                "duration": self.duration,
                                "user_id": schedule.user_id.id,
                                "repeat_weekly": 0,
                                "parent_ids": schedule.id,
                                "is_parent": False,
                            }
                        )
                schedules_to_create.extend(new_schedules)

        self.env["meeting.schedule"].create(schedules_to_create)

    def _check_is_hr(self):
        return bool(self.env.user.has_group("meeting_room.group_meeting_room_hr"))

    def _check_is_past_date(self, start_date):
        if start_date is None:
            return False
        if not isinstance(start_date, datetime):
            start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        return start_date < fields.Datetime.now()

    # CRUD Methods
    @api.model
    def create(self, vals):
        meeting_schedule = super(MeetingSchedule, self).create(vals)
        start_date = vals.get("start_date")

        if not self._check_is_hr() and self._check_is_past_date(start_date):
            raise ValidationError("Start date cannot be in the past")

        meeting_type = vals.get("meeting_type")
        monday = vals.get("monday")
        if meeting_type == "daily":
            meeting_schedule.create_daily()
        elif meeting_type == "weekly":
            meeting_schedule.create_weekly()
        return meeting_schedule

    def write(self, vals):
        for record in self:
            start_date = vals.get("start_date")
            end_date = vals.get("end_date")

            if not record._check_is_hr():
                if self._check_is_past_date(record.start_date):
                    raise ValidationError("Cannot edit ongoing or finished meetings")
                if self._check_is_past_date(start_date):
                    raise ValidationError("Start date cannot be in the past")

            if "meeting_type" in vals:
                raise ValidationError("You cannot edit the meeting type.")
            if "repeat_weekly" in vals:
                raise ValidationError("You cannot edit the repeat weekly.")

            if start_date:
                start_date = parser.parse(start_date).date()
            if end_date:
                end_date = parser.parse(end_date).date()
            if start_date:
                self.write(
                    {
                        "start_daily": fields.Date.to_string(start_date),
                        "end_daily": (
                            fields.Date.to_string(end_date) if end_date else False
                        ),
                    }
                )

        return super(MeetingSchedule, self).write(vals)

    def unlink(self):
        for record in self:
            if not record._check_is_hr() and record._check_is_past_date(
                start_date=record.start_date
            ):
                raise ValidationError("Cannot delete ongoing or finished meetings.")
        return super(MeetingSchedule, self).unlink()

    def save(self):
        self.env.cr.commit()
        return {'type': 'ir.actions.act_window_close'}