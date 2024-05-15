from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta, datetime
from pytz import timezone

def generate_time_selection():
    time_selection = []
    start_hour = 0
    end_hour = 23
    end_minute = 30
    interval_minutes = 15

    for hour in range(start_hour, end_hour + 1):
        for minute in range(0, 60, interval_minutes):
            if hour == end_hour and minute > end_minute:
                break
            formatted_hour = str(hour).zfill(2)
            formatted_minute = str(minute).zfill(2)
            if hour >= 12:
                time_label = f"{formatted_hour}:{formatted_minute}"
            else:
                time_label = f"{formatted_hour}:{formatted_minute}"
            time_selection.append(
                (f"{formatted_hour}:{formatted_minute}", time_label)
            )
    return time_selection

class MeetingSchedule(models.Model):
    _name = "meeting.schedule"
    _description = "Meeting schedule"
    _order = "start_date DESC"
    _rec_name = "name"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Name", compute="_compute_meeting_name", required=True)
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
    start_date = fields.Datetime(string="Start Date Time", required=True)
    end_date = fields.Datetime(string="End Date Time", required=True)
    s_date = fields.Date(string="Start Date", required=True)
    e_date = fields.Date(string="End Date", required=True)

    start_minutes = fields.Selection(
        generate_time_selection(),
        string="Start",
        compute = '_compute_default_start_minutes',
        store=False,
        required=True
    )
    end_minutes = fields.Selection(
        generate_time_selection(),
        string="End",
        compute = '_compute_default_end_minutes',
        store=False,
        required=True
    )
    duration = fields.Float(
        string="Duration(hour)",
        compute="_compute_duration",
        store=True,
    )
    room_id = fields.Many2one("meeting.room", string="Room", required=True)
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
    day = fields.Char("Day", compute="_compute_kanban_date_start", store=True,)
    month = fields.Char("Month and Year", compute="_compute_kanban_date_start", store=True,)
    time = fields.Char("Time", compute="_compute_kanban_date_start", store=True,)

    repeat_weekly = fields.Integer(string="Repeat Weekly", default=1)
    weekday = fields.Char(string="Day of week")

    monday = fields.Boolean(string="Monday", default=True, readonly=False)
    tuesday = fields.Boolean(string="Tuesday", default=True, readonly=False)
    wednesday = fields.Boolean(string="Wednesday", default=True, readonly=False)
    thursday = fields.Boolean(string="Thursday", default=True, readonly=False)
    friday = fields.Boolean(string="Friday", default=True, readonly=False)
    saturday = fields.Boolean(string="Saturday", default=False, readonly=False)
    sunday = fields.Boolean(string="Sunday", default=False, readonly=False)

    is_edit = fields.Boolean(default=False)
    is_first_tag = fields.Boolean(default=True)
    check_access_team_id = fields.Boolean("Check Access", compute="_check_user_id")

    attachment_ids = fields.One2many('ir.attachment','res_id', string="Attachments") 
    file_attachment_ids = fields.Many2many('ir.attachment', string="Attach File", inverse='_inverse_file_attachment_ids')
    
    partner_ids = fields.Many2many(comodel_name="hr.employee", string="Attendees")
    for_attachment = fields.Boolean(default=True, compute="_check_for_attachment")
    customize = fields.Boolean(string="Customize", default=False)

    def _compute_default_start_minutes(self):
        time_start_date =  self.start_date.astimezone(self.get_local_tz()) 
        start_hour = time_start_date.hour
        start_minute = time_start_date.minute
        self.start_minutes = f"{start_hour:02d}:{start_minute:02d}"

    def _compute_default_end_minutes(self):
        time_end_date =  self.end_date.astimezone(self.get_local_tz())
        end_hour = time_end_date.hour
        end_minute = time_end_date.minute
        self.end_minutes = f"{end_hour:02d}:{end_minute:02d}"

    def _inverse_file_attachment_ids(self):
        self.attachment_ids = self.file_attachment_ids
        return

    #Depends
    @api.depends("user_id")
    def _check_user_id(self):
        for rec in self:
            rec.check_access_team_id = bool(rec._check_is_hr() or rec.user_id.id == self.env.uid)

    @api.depends("partner_ids")
    def _check_for_attachment(self):
        for rec in self:
            is_hr = rec._check_is_hr()
            rec.for_attachment = bool(
                is_hr or
                self.env.user.id == rec.create_uid.id or
                any(partner.id in rec.partner_ids.ids for partner in rec.partner_ids)
            )

    @api.depends("room_id", "user_id")
    def _compute_meeting_name(self):
        for record in self:
            if record.room_id and record.user_id:
                record.name = f"{record.room_id.name} - {record.user_id.name}"

    @api.depends("start_date")
    def _compute_kanban_date_start(self):
        for record in self:
            if record.start_date:
                date_obj = record.start_date.astimezone(self.get_local_tz())
                record.day = date_obj.strftime("%-d")
                record.month = date_obj.strftime("%b %Y")
                record.time = date_obj.strftime("%H:%M")

    @api.depends("start_date", "end_date")
    def _compute_duration(self):
        for record in self:
            if record.start_date and record.end_date:

                start_time = record.start_date.astimezone(self.get_local_tz()).time()
                end_time = record.end_date.astimezone(self.get_local_tz()).time()

                start_seconds = (start_time.hour * 3600 + start_time.minute * 60 + start_time.second)
                end_seconds = (end_time.hour * 3600 + end_time.minute * 60 + end_time.second)

                duration_seconds = end_seconds - start_seconds
                duration_hours = duration_seconds / 3600
                record.duration = duration_hours

    # Constraints
    @api.constrains('file_attachment_ids')
    def _check_file_attachment_ids(self):
        for record in self:
            if len(record.file_attachment_ids) > 1:
                raise ValidationError("You can only attach one file.")

    @api.constrains("duration")
    def _check_duration(self):
        for schedule in self:
            if schedule.duration < 0.25:
                raise ValidationError("A meeting must be at least 15 minutes")

    @api.constrains("repeat_weekly")
    def _check_max_value(self):
        for record in self:
            if record.repeat_weekly > 52:
                raise ValidationError("Cannot repeat for more than a year")

    @api.constrains("start_date", "duration", "room_id")
    def _check_room_availability(self):
        for record in self:
            if record.start_date and record.duration and record.room_id:
                start_datetime = record.start_date
                end_datetime = start_datetime + timedelta(hours=record.duration)

                conflicting_bookings = self.search(
                    [
                        ("room_id", "=", record.room_id.id),
                        ("id", "!=", record.id),
                        ("start_date", "<", end_datetime),
                        ("end_date", ">", start_datetime),
                    ]
                )
                if conflicting_bookings:
                    raise ValidationError("The room is already booked for this time period.")

    @api.constrains("file_attachment_ids")
    def _validate_attachment(self):
        allowed_extensions = ["txt","doc","docx","xlsx","csv","ppt","pptx","pdf","png","jpg","jpeg"]

        for record in self:
            
            if record.file_attachment_ids:
                if "." not in record.file_attachment_ids.name \
                or record.file_attachment_ids.name.rsplit(".", 1)[1].lower() not in allowed_extensions:
                    raise ValidationError("Invalid attachment file type")
                max_file_size = 10 * 1000 * 1000
                if record.file_attachment_ids.file_size > max_file_size:
                    size_in_mb =record.file_attachment_ids.file_size /1000 /1000
                    raise ValidationError(
                        f"Attachment file size is {round(size_in_mb,2)} MB "
                        f"which exceeds the maximum file size allowed of {max_file_size / 1000 / 1000} MB"
                    )
                    
    # Onchanges
    @api.onchange("start_date", "end_date")
    def _onchange_start_end_date(self):
        if self.start_date and self.end_date:
            start_date = self.start_date.astimezone(self.get_local_tz()) 
            end_date = self.end_date.astimezone(self.get_local_tz()) 
            
            start_seconds = start_date.hour * 3600 + start_date.minute * 60 + start_date.second
            end_seconds = end_date.hour * 3600 + end_date.minute * 60 + end_date.second
                
            duration_seconds = end_seconds - start_seconds
            duration_hours = duration_seconds / 3600
            self.duration = duration_hours

            self.start_minutes = str(start_date.hour).zfill(2) + ":" + str(start_date.minute).zfill(2)
            self.end_minutes = str(end_date.hour).zfill(2) + ":" + str(end_date.minute).zfill(2)          
        
            if self.duration != 0 and end_date.date() != start_date.date() and self.meeting_type != "daily" :
                self.meeting_type = "daily"

    @api.onchange("start_date")
    def _onchange_start_date(self):
        if self.start_date:
            local_offset = self.get_local_tz(True)
            adjusted_start_date = self.start_date + timedelta(hours=local_offset)
            self.weekday = adjusted_start_date.strftime("%A")
            self.s_date = fields.Date.to_string(adjusted_start_date.date())

    @api.onchange("end_date")
    def _onchange_end_date(self):
        if self.end_date:
            local_offset = self.get_local_tz(True)
            adjusted_end_date = self.end_date + timedelta(hours=local_offset)
            self.e_date = fields.Date.to_string(adjusted_end_date.date())

    @api.onchange("s_date", "start_minutes")
    def onchange_s_date(self):
        if self.s_date and self.start_minutes:
            local_offset = self.get_local_tz(True)
            time_obj = datetime.strptime(self.start_minutes, "%H:%M").time()
            combined_datetime = datetime.combine(self.s_date, time_obj)
            self.start_date = combined_datetime - timedelta(hours=local_offset)

    @api.onchange("e_date", "end_minutes")
    def onchange_e_date(self):
        if self.e_date and self.end_minutes:
            local_offset = self.get_local_tz(True)
            time_obj = datetime.strptime(self.end_minutes, "%H:%M").time()
            combined_datetime = datetime.combine(self.e_date, time_obj)
            self.end_date = combined_datetime - timedelta(hours=local_offset)

    @api.onchange("meeting_type")
    def onchange_meeting_type(self):
        if self.meeting_type != "daily" and self.s_date != self.e_date:
            self.end_date = self.end_date.replace(day=self.start_date.day
            ,month = self.start_date.month
            ,year=self.start_date.year)

    @api.onchange("start_date", "meeting_type")
    def onchange_start_time(self):
        if self.start_date and self.meeting_type:
            if self.meeting_type == "daily":
                self.monday = self.tuesday = self.wednesday = self.thursday = self.friday = True
                self.saturday = self.sunday = False
            elif self.meeting_type == "weekly":
                self.monday = self.tuesday = self.wednesday = self.thursday = self.friday = self.saturday = self.sunday = False
                local_start = self.start_date.astimezone(self.get_local_tz())
                day_of_week = local_start.weekday()
                days = {0: 'monday', 1: 'tuesday', 2: 'wednesday', 3: 'thursday', 4: 'friday', 5: 'saturday', 6: 'sunday'}
                setattr(self, days[day_of_week], True)

    # Business Logic Methods
    def create_daily(self):
        start_datetime = self.start_date
        end_datetime = self.end_date
        end_date = datetime.combine(start_datetime.date(), end_datetime.time())

        hours = self.get_local_tz(offset=True)

        local_start_datetime = (start_datetime + timedelta(hours=hours)).date()
        local_end_datetime = (end_datetime + timedelta(hours=hours)).date()

        new_end_date = ""
        
        if local_start_datetime == start_datetime.date():
            new_end_date = end_date
        elif local_start_datetime > start_datetime.date():
            if local_end_datetime > end_datetime.date():
                new_end_date = end_date
            elif local_end_datetime == end_datetime.date():
                new_end_date = end_date + timedelta(days=1)

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
        weekday_mapping = dict(zip(range(len(weekday_attributes)), weekday_attributes))

        booking_dates = [
            start_datetime + timedelta(days=day)
            for day in range(1, (end_datetime - start_datetime).days + 1)
        ]

        booking_to_create = []

        for booking in booking_dates:
            if weekday_mapping.get(booking.weekday(), False):
                booking_to_create.append({
                    "name": self.name,
                    "meeting_subject": self.meeting_subject,
                    "description": self.description,
                    "meeting_type": "normal",
                    "start_date": booking,
                    "end_date": datetime.combine(booking.date(), end_datetime.time()),
                    "duration": self.duration,
                    "file_attachment_ids": self.file_attachment_ids,
                    "room_id": self.room_id.id,
                    "company_id": self.company_id.id,
                    "user_id": self.user_id.id,
                    "is_edit": True,
                    "is_first_tag": False,
                    "partner_ids": self.partner_ids,
                    's_date': booking.date(),
                    'e_date': booking.date(),
                })

        self.create(booking_to_create)

    def create_weekly(self):
        booking_to_create = []
        for rec in self:
            start_date = rec.start_date

            self.write({"meeting_type": "normal"})

            for i in range(rec.repeat_weekly + 1):
                new_bookings = []
                current_date = start_date + timedelta(weeks=i)
                if current_date != start_date:
                    new_bookings.append(
                        {
                            "name": rec.room_id.name,
                            "meeting_subject": rec.meeting_subject,
                            "description": rec.description,
                            "start_date": current_date,
                            "end_date": current_date + timedelta(hours=rec.duration),
                            "meeting_type": "normal",
                            "room_id": rec.room_id.id,
                            "company_id": rec.company_id.id,
                            "duration": self.duration,
                            "file_attachment_ids": rec.file_attachment_ids,
                            "user_id": rec.user_id.id,
                            "repeat_weekly": 0,
                            "is_edit": True,
                            "is_first_tag": False,
                            "partner_ids": self.partner_ids,
                            's_date': current_date.date(),
                            'e_date': (current_date + timedelta(hours=rec.duration)).date()
                        }
                    )
                booking_to_create.extend(new_bookings)

        self.create(booking_to_create)

    def _check_is_hr(self):
        return self.env.user.has_group("booking_room.group_booking_room_hr")

    def _check_is_past_date(self, start_date):
        if start_date is None:
            return False
        if not isinstance(start_date, datetime):
            start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        return start_date < fields.Datetime.now()

    def _validate_start_date(self):
        user_tz = self.env.user.tz or "UTC"
        local_tz = timezone(user_tz)
        start_datetime = self.start_date.astimezone(local_tz)

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

    

    def send_email_to_attendees(self):
            mail_template = "booking_room.invite_meeting_mail_template"
            subject_template = "[Meeting] Invite Meeting Attendance"
            self._send_message_auto_subscribe_notify(
                self.partner_ids, mail_template, subject_template
            )

    @api.model
    def _send_message_auto_subscribe_notify(self, employees, mail_template, subject_template):
        template_id = self.env["ir.model.data"]._xmlid_to_res_id(mail_template, raise_if_not_found=False)
        if not template_id:
            return
        view = self.env["ir.ui.view"].browse(template_id)

        email_addresses = employees.mapped('work_email')
        email_addresses = list(filter(None, email_addresses))  # Remove any empty email addresses

        if not email_addresses:
            return

        date_obj = fields.Datetime.to_string(
            fields.Datetime.context_timestamp(self, fields.Datetime.from_string(self.start_date))
        )

        values = {
            "object": self,
            "date_obj": date_obj,
            "model_description": "Invite meeting",
            "access_link": self._notify_get_action_link("view"),
        }

        assignation_msg = view._render(values, engine="ir.qweb", minimal_qcontext=True)
        assignation_msg = self.env["mail.render.mixin"]._replace_local_links(assignation_msg)

        mail_values = {
            'subject': subject_template,
            'body_html': assignation_msg,
            'email_to': ','.join(email_addresses),
            'email_from': self.env.user.email or '',
        }

        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()

    def get_local_tz(self, offset=False):
        user_tz = self.env.user.tz or "UTC"
        if offset:
            tz_offset = timezone(user_tz).utcoffset(datetime.now()).total_seconds() // 3600
            return tz_offset
        return timezone(user_tz)

    # CRUD Methods
    @api.model
    def create(self, vals):
        start_date = vals.get("start_date")
        if not self._check_is_hr() and self._check_is_past_date(start_date):
            raise ValidationError("Start date cannot be in the past")
        vals["is_edit"] = True
        meeting_schedule = super(MeetingSchedule, self).create(vals)

        meeting_schedule._validate_start_date()

        meeting_type = vals.get("meeting_type")

        if meeting_type == "daily":
            meeting_schedule.create_daily()
        elif meeting_type == "weekly":
            meeting_schedule.create_weekly()
        if vals["is_first_tag"] == True \
        and "partner_ids" in vals \
        and len(vals["partner_ids"][0][2]) > 0:
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
            if not record._check_is_hr() and record._check_is_past_date(start_date=record.start_date):
                raise ValidationError("Cannot delete ongoing or finished meetings.")
        return super(MeetingSchedule, self).unlink()

    @api.model
    def delete_meeting(self, selected_value, id):
        find_meeting = self.search([("id", "=", id)])
        if self._check_is_hr() == True:
            if selected_value == "self_only":
                find_meeting.unlink()
            elif selected_value == "future_events":
                record_to_detele = self.search([("start_date", ">=", find_meeting.start_date)])
                find_meeting.unlink()
                record_to_detele.unlink()
            else:
                record_to_detele = self.search([])
                record_to_detele.unlink()
        else:
            if find_meeting.user_id.id == self.env.uid:
                if selected_value == "self_only":
                    if self._check_is_past_date(find_meeting.start_date):
                        raise Exception("Cannot delete ongoing or finished meetings.")
                    return super(MeetingSchedule, find_meeting).unlink()
                elif selected_value == "future_events":
                    record_to_detele = self.search(
                        [
                            ("start_date", ">=", find_meeting.start_date),
                            ("create_uid", "=", self.env.uid),
                        ]
                    )
                    return super(MeetingSchedule, record_to_detele).unlink()
                else:
                    record_to_detele = self.search(
                        [
                            ("start_date", ">=", fields.Datetime.now()),
                            ("create_uid", "=", self.env.uid),
                        ]
                    )
                    return super(MeetingSchedule, record_to_detele).unlink()

            raise Exception("You cannot delete someone else's meeting.")

    @api.model
    def check_hr(self):
        return self.env.user.has_group("booking_room.group_booking_room_hr")