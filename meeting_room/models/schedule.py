from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta, datetime
from pytz import timezone
import base64
from collections import defaultdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
import smtplib
from datetime import timedelta, datetime, date
import pytz
import socket


class MeetingSchedule(models.Model):
    _name = "meeting.schedule"
    _description = "Meeting schedule"
    _order = "start_date DESC"

    name = fields.Char(
        string="Name", compute="_compute_meeting_name", required=True
    )
    meeting_subject = fields.Char(string="Meeting subject")
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
    start_date = fields.Datetime(
        string="Start datetime",
        default=fields.Date.context_today,
    )
    end_date = fields.Datetime(string="End datetime", default=fields.Date.context_today)

    duration = fields.Float(
        string="Duration(hour)",
        compute="_compute_duration",
        store=True,
    )
    duration_minutes = fields.Integer(
        string="Duration(minutes)",
        compute="_compute_duration_minutes",
        store=True,
    )
    room_id = fields.Many2one("meeting.room", string="Room", ondelete="cascade")
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
    weekday = fields.Char(string="Day of week", compute="_compute_weekday_selected")

    monday = fields.Boolean(string="Monday", default=True, readonly=False)
    tuesday = fields.Boolean(string="Tuesday", default=True, readonly=False)
    wednesday = fields.Boolean(string="Wednesday", default=True, readonly=False)
    thursday = fields.Boolean(string="Thursday", default=True, readonly=False)
    friday = fields.Boolean(string="Friday", default=True, readonly=False)
    saturday = fields.Boolean(string="Saturday", default=False, readonly=False)
    sunday = fields.Boolean(string="Sunday", default=False, readonly=False)

    is_edit = fields.Boolean(default=False)
    is_first_tag = fields.Boolean(default=True)
    check_access_team_id = fields.Boolean(
        "Check Access", compute="_compute_access_team_id"
    )

    attachment = fields.Binary(
        compute="_compute_content",
        inverse="_inverse_content",
        attachment=False,
        prefetch=False,
        store=False,
    )
    content_binary = fields.Binary(attachment=False, prefetch=False, invisible=True)
    content_file = fields.Binary(attachment=True, prefetch=False, invisible=True)
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Attachment File",
        prefetch=False,
        invisible=True,
        ondelete="cascade",
    )
    filename = fields.Char("Attachment Name")
    hide_attachment_field = fields.Boolean(
        compute="_compute_hide_attachment_field", string="Hide Attachment Field"
    )

    partner_ids = fields.Many2many(
        "res.partner",
        string="Attendees",
    )
    employee_id = fields.Many2many(
        "hr.employee",
        string="Attendees",
        store=False,
    )

    tatol_id = fields.Char(
        string = "Send to",
        readonly=True
    )
    is_partner = fields.Boolean(default=True, compute="check_user_in_partner_ids")
    customize = fields.Boolean(string="Customize", default=False)
    is_same_date = fields.Boolean(default=True)
    is_long_meeting = fields.Boolean(default=True)

    # upload + download document
    def _inverse_content(self):
        updates = defaultdict(set)
        for record in self:
            values = self._get_content_inital_vals()
            values = record._update_content_vals(values)
            updates[tools.frozendict(values)].add(record.id)
        with self.env.norecompute():
            for vals, ids in updates.items():
                self.browse(ids).write(dict(vals))

    # Depend Fields
    @api.depends("content_binary", "content_file", "attachment_id")
    def _compute_content(self):
        for record in self:
            if record.content_file:
                context = {"base64": True}
                record.attachment = record.with_context(**context).content_file
            elif record.content_binary:
                record.attachment = base64.b64encode(record.content_binary)
            elif record.attachment_id:
                context = {"base64": True}
                record.attachment = record.with_context(**context).attachment_id.datas

    @api.depends("user_id")
    def check_user_in_partner_ids(self):
        for rec in self:
            rec.is_partner = bool(
                rec._check_is_hr() or self.env.user.partner_id.id in rec.partner_ids.ids
            )

    @api.depends("user_id")
    def _compute_access_team_id(self):
        for rec in self:
            rec.check_access_team_id = bool(
                rec._check_is_hr() or rec.user_id.id == self.env.uid
            )

    @api.depends("name")
    def _compute_meeting_name(self):
        for record in self:
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

    @api.depends("start_date", "end_date", "duration")
    def _compute_duration(self):
        for record in self:
            if record.start_date and record.end_date:
                user_tz = self.env.user.tz or "UTC"
                local_tz = timezone(user_tz)
                start_time = (
                    fields.Datetime.from_string(record.start_date)
                    .astimezone(local_tz)
                    .time()
                )
                end_time = (
                    fields.Datetime.from_string(record.end_date)
                    .astimezone(local_tz)
                    .time()
                )

                start_seconds = (
                    start_time.hour * 3600 + start_time.minute * 60 + start_time.second
                )
                end_seconds = (
                    end_time.hour * 3600 + end_time.minute * 60 + end_time.second
                )

                duration_seconds = end_seconds - start_seconds
                duration_hours = duration_seconds / 3600
                record.duration = duration_hours

    @api.depends("start_date", "end_date")
    def _compute_duration_minutes(self):
        for record in self:
            if record.start_date and record.end_date:
                duration = record.end_date - record.start_date
                minutes = duration.total_seconds() // 60
                record.duration_minutes = int(minutes)

    # Constraints
    @api.constrains("duration")
    def _check_duration(self):
        for schedule in self:
            if schedule.duration < 0.25:
                raise ValidationError("A meeting must be at least 15 minutes")

    @api.constrains("start_date", "end_date")
    def _check_date(self):
        for record in self:
            user_tz = self.env.user.tz or "UTC"
            local_tz = timezone(user_tz)
            start_date = fields.Datetime.from_string(record.start_date).astimezone(
                local_tz
            )
            end_date = fields.Datetime.from_string(record.end_date).astimezone(local_tz)
            if record.meeting_type != "daily" and start_date.date() != end_date.date():
                raise ValidationError("The meeting must end within the same date")

    @api.constrains("repeat_weekly")
    def _check_max_value(self):
        for record in self:
            if record.repeat_weekly > 10:
                raise ValidationError("Maximum weekly meeting allowed is 10.")

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

    # Onchange
    @api.onchange("start_date")
    def _compute_weekday_selected(self):
        self.weekday = self.convert_to_local(
            str(self.start_date), "Asia/Ho_Chi_Minh"
        ).strftime("%A")

    @api.onchange("start_date", "end_date")
    def _onchange_compute_duration(self):
        local_start = self.convert_to_local(str(self.start_date), "Asia/Ho_Chi_Minh")
        local_end = self.convert_to_local(str(self.end_date), "Asia/Ho_Chi_Minh")
        number_date = local_end - local_start
        for item in range(0, number_date.days + 1):
            newday = local_start
            if newday.weekday() == 0:
                self.monday = {"readonly": True}
            elif newday.weekday() == 1:
                self.tuesday = {"readonly": True}
            elif newday.weekday() == 2:
                self.wednesday = {"readonly": True}
            elif newday.weekday() == 3:
                self.thursday = {"readonly": True}
            elif newday.weekday() == 4:
                self.friday = {"readonly": True}
            elif newday.weekday() == 5:
                self.saturday = {"readonly": True}
            else:
                self.sunday = {"readonly": True}

            local_start += timedelta(days=1)

        for record in self:
            if record.start_date and record.end_date:
                user_tz = self.env.user.tz or "UTC"
                local_tz = timezone(user_tz)
                start_time = (
                    fields.Datetime.from_string(record.start_date)
                    .astimezone(local_tz)
                    .time()
                )
                end_time = (
                    fields.Datetime.from_string(record.end_date)
                    .astimezone(local_tz)
                    .time()
                )

                start_seconds = (
                    start_time.hour * 3600 + start_time.minute * 60 + start_time.second
                )
                end_seconds = (
                    end_time.hour * 3600 + end_time.minute * 60 + end_time.second
                )

                duration_seconds = end_seconds - start_seconds
                duration_hours = duration_seconds / 3600
                record.duration = duration_hours

    @api.onchange("duration_minutes")
    def onchange_duration_minutes(self):
        for record in self:
            if record.duration_minutes:
                record.end_date = record.start_date + timedelta(
                    minutes=record.duration_minutes
                )
                if record.duration_minutes < 15:
                    record.is_long_meeting = False
                else:
                    record.is_long_meeting = True

    @api.onchange("start_date", "end_date", "meeting_type")
    def onchange_check_date(self):
        for record in self:
            user_tz = self.env.user.tz or "UTC"
            local_tz = timezone(user_tz)
            start_date = fields.Datetime.from_string(record.start_date).astimezone(
                local_tz
            )
            end_date = fields.Datetime.from_string(record.end_date).astimezone(local_tz)
            if (
                record.meeting_type != "daily"
                and start_date.date() != end_date.date()
                and record.duration_minutes != 0
            ):
                record.is_same_date = False
            else:
                record.is_same_date = True

    @api.onchange("start_date", "meeting_type")
    def onchange_start_time(self):
        if self.meeting_type == "daily":
            self.monday = True
            self.tuesday = True
            self.thursday = True
            self.wednesday = True
            self.friday = True
            self.saturday = False
            self.sunday = False
        if self.meeting_type == "weekly":
            self.monday = False
            self.tuesday = False
            self.thursday = False
            self.wednesday = False
            self.friday = False
            self.saturday = False
            self.sunday = False

            local_start = self.convert_to_local(
                str(self.start_date), "Asia/Ho_Chi_Minh"
            )
            day_of_week = local_start.weekday()
            if day_of_week == 0:
                self.monday = True
            elif day_of_week == 1:
                self.tuesday = True
            elif day_of_week == 2:

                self.wednesday = True
            elif day_of_week == 3:
                self.thursday = True
            elif day_of_week == 4:
                self.friday = True
            elif day_of_week == 5:
                self.saturday = True
            elif day_of_week == 6:
                self.sunday = True

    @api.onchange("start_date", "end_date")
    def _onchange_duration_minutes(self):
        for record in self:
            if record.start_date and record.end_date:
                duration = record.end_date - record.start_date
                minutes = duration.total_seconds() // 60
                record.duration_minutes = int(minutes)

    # Business Logic Methods
    def create_daily(self):
        start_datetime = fields.Datetime.from_string(self.start_date)
        end_datetime = fields.Datetime.from_string(self.end_date)
        end_date = datetime.combine(start_datetime.date(), end_datetime.time())

        new_end_date = ""

        if (start_datetime + timedelta(hours=7)).date() == start_datetime.date():
            new_end_date = fields.Datetime.to_string(end_date)
        elif (start_datetime + timedelta(hours=7)).date() > start_datetime.date():
            if (end_datetime + timedelta(hours=7)).date() > end_datetime.date():
                new_end_date = fields.Datetime.to_string(end_date)
            elif (end_datetime + timedelta(hours=7)).date() == end_datetime.date():
                new_end_date = fields.Datetime.to_string(end_date + timedelta(days=1))

        self.write({"end_date": new_end_date, "meeting_type": "normal"})

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
                        "meeting_type": "normal",
                        "start_date": fields.Datetime.to_string(meeting_date),
                        "end_date": fields.Datetime.to_string(
                            datetime.combine(meeting_date.date(), end_datetime.time())
                        ),
                        "duration": self.duration,
                        "room_id": self.room_id.id,
                        "company_id": self.company_id.id,
                        "user_id": self.user_id.id,
                        "is_edit": True,
                        "is_first_tag": False,
                    }
                )

    def create_weekly(self):
        schedules_to_create = []
        for schedule in self:
            start_date = fields.Datetime.from_string(schedule.start_date)

            self.write({"meeting_type": "normal"})

            for i in range(schedule.repeat_weekly + 1):
                new_schedules = []
                current_date = start_date + timedelta(weeks=i)
                if current_date != start_date:
                    new_schedules.append(
                        {
                            "name": schedule.room_id.name,
                            "meeting_subject": schedule.meeting_subject,
                            "description": schedule.description,
                            "start_date": current_date,
                            "end_date": current_date
                            + timedelta(minutes=self.duration_minutes),
                            "meeting_type": "normal",
                            "room_id": schedule.room_id.id,
                            "company_id": schedule.company_id.id,
                            "duration": self.duration,
                            "user_id": schedule.user_id.id,
                            "repeat_weekly": 0,
                            "is_edit": True,
                            "is_first_tag": False,
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

    def _validate_start_date(self):
        user_tz = self.env.user.tz or "UTC"
        local_tz = timezone(user_tz)
        start_datetime = fields.Datetime.from_string(self.start_date).astimezone(
            local_tz
        )

        weekday_mapping = {
            0: ("Monday", self.monday),
            1: ("Tuesday", self.tuesday),
            2: ("Wednesday", self.wednesday),
            3: ("Thursday", self.thursday),
            4: ("Friday", self.friday),
            5: ("Saturday", self.saturday),
            6: ("Sunday", self.sunday),
        }
        weekday_name, allowed = weekday_mapping.get(start_datetime.weekday())
        if not allowed and self.meeting_type == "daily" and self.is_first_tag == True:
            raise ValidationError(f"Start date cannot be scheduled on {weekday_name}.")

    def _get_content_inital_vals(self):
        return {"content_binary": False, "content_file": False}

    def _update_content_vals(self, vals):
        new_vals = vals.copy()
        new_vals["content_file"] = self.attachment
        return new_vals

    def send_email_to_attendees(self):
        subject = "Meeting Attendance"
        sender = self.user_id.email
        recipients = self.partner_ids.mapped("email")

        start_date = self.start_date
        date_obj = fields.Datetime.to_string(
            fields.Datetime.context_timestamp(
                self, fields.Datetime.from_string(start_date)
            )
        )

        room_id = str(self.room_id.id)

        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        port = 8069
        id = self.id
        url = f"http://{ip_address}:{port}/web#id={id}&menu_id=457&action=558&model=meeting.schedule&view_type=form"
        body = f"Hello, You are invited to a meeting. Please attend at {date_obj}, room {room_id}.\n\nLink: {url}"

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        msg["Date"] = formatdate(localtime=True)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(self.user_id.email, "wris tnin qncg fkng")
        server.sendmail(sender, recipients, msg.as_string())
        server.quit()
        self._cr.commit()

    def convert_to_local(self, utc_datetime=None, timezone="utc"):
        """Convert UTC time to Localtime"""
        utc_datetime = datetime.strptime(utc_datetime, "%Y-%m-%d %H:%M:%S")
        utc = pytz.timezone("UTC")
        utc_dt = utc.localize(utc_datetime)
        local = pytz.timezone(timezone)
        local_dt = utc_dt.astimezone(local)
        local_dt = local_dt.replace(tzinfo=None)

        return local_dt

    # CRUD Methods
    @api.model
    def create(self, vals):
        activity_user_ids = [str(item[2]['activity_user_id']) for item in vals['employee_id'] if len(item) >= 3 and isinstance(item[2], dict) and isinstance(item[2].get('activity_user_id'), int)]
        activity_user_id_str = ",".join(activity_user_ids)
        elements = activity_user_id_str.split(",")
        elements = list(set(int(element) for element in elements))

        tatol_user=""
        for item in elements:
            find_meeting = self.env["res.users"].search(
            [
                ("id", "=", item),
            ]
            )
            tatol_user= tatol_user + str(find_meeting.name) + ","
        vals['tatol_id'] = tatol_user
        vals['employee_id']= None 

        start_date = vals.get("start_date")
        global id
        vals["is_edit"] = True
        meeting_schedule = super(MeetingSchedule, self).create(vals)

        if not self._check_is_hr() and self._check_is_past_date(start_date):
            raise ValidationError("Start date cannot be in the past")

        meeting_schedule._validate_start_date()

        meeting_type = vals.get("meeting_type")
        if meeting_type == "daily":
            meeting_schedule.create_daily()
        elif meeting_type == "weekly":
            meeting_schedule.create_weekly()
        if "partner_ids" in vals and len(vals["partner_ids"][0][2]) > 0:
            id = meeting_schedule.id
            meeting_schedule.send_email_to_attendees()
        return meeting_schedule

    def write(self, vals):
        for record in self:
            start_date = vals.get("start_date")

            if not record._check_is_hr():
                if self._check_is_past_date(record.start_date):
                    raise ValidationError("Cannot edit ongoing or finished meetings")
                if self._check_is_past_date(start_date):
                    raise ValidationError("Start date cannot be in the past")
        return super(MeetingSchedule, self).write(vals)

    def unlink(self):
        for record in self:
            if not record._check_is_hr() and record._check_is_past_date(
                start_date=record.start_date
            ):
                raise ValidationError("Cannot delete ongoing or finished meetings.")
        return super(MeetingSchedule, self).unlink()

    @api.model
    def delete_meeting(self, selected_value, dateStart):
        id = dateStart
        find_meeting = self.env["meeting.schedule"].search(
            [
                ("id", "=", id),
            ]
        )
        print(id, "***")
        if self._check_is_hr() == True:
            if selected_value == "self_only":
                find_meeting.unlink()
            elif selected_value == "future_events":
                record_to_detele = self.env["meeting.schedule"].search(
                    [
                        ("start_date", ">=", find_meeting.start_date),
                    ]
                )
                find_meeting.unlink()
                record_to_detele.unlink()
            else:
                record_to_detele = self.env["meeting.schedule"].search([])
                record_to_detele.unlink()
        else:
            if find_meeting.user_id.id == self.env.uid:
                if selected_value == "self_only":
                    if self._check_is_past_date(find_meeting.start_date):
                        raise Exception(
                            "Cannot delete ongoing or finished meetings."
                        )
                    return super(MeetingSchedule, find_meeting).unlink()
                elif selected_value == "future_events":
                    record_to_detele = self.env["meeting.schedule"].search(
                        [
                            ("start_date", ">=", find_meeting.start_date),
                            ("create_uid", "=", self.env.uid),
                        ]
                    )
                    return super(MeetingSchedule, record_to_detele).unlink()
                else:
                    record_to_detele = self.env["meeting.schedule"].search(
                        [
                            ("start_date", ">=", fields.Datetime.now()),
                            ("create_uid", "=", self.env.uid),
                        ]
                    )
                    return super(MeetingSchedule, record_to_detele).unlink()

            raise Exception("You cannot delete someone else's meeting.")
