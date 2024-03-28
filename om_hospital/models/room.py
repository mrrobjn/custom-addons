from odoo import api, fields, models


class HospitalRoom(models.Model):
    _name = "hospital.room"
    _description = "Hospital room"

    name = fields.Char(string="Name")
    bed = fields.Integer(string="Number of bed")
