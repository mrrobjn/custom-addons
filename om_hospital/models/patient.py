from odoo import fields, models


class HospitalPatient(models.Model):
    _name = "hospital.patient"
    _description = "Hospital patient"

    name = fields.Char(string="Name")
    ref = fields.Char(string="Reference")
    age = fields.Integer(string="Age")
    gender = fields.Selection(
        [("male", "Male"), ("female", "Female")],
        string="Gender",
        default="male",
        required=True,
    )
    active = fields.Boolean(string="Active", default=True)
