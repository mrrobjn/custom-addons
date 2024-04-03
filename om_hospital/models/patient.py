from odoo import fields, models, api
from odoo.exceptions import ValidationError


class HospitalPatient(models.Model):
    _name = "hospital.patient"
    _inherit = ["mail.thread", "mail.activity.mixin"]
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
    appointment_ids = fields.One2many('hospital.appointment', 'patient_id', string="Hospital appointment")


    def action_view_patient(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Patient detail",
            "view_mode": "form",
            "res_model": "hospital.patient",
            'res_id': self.id,  # Uncomment if you want to open a specific record
            "target": "new",
        }

    @api.constrains("name", "ref")
    def _check_ref(self):
        for record in self:
            if record.name == record.ref:
                raise ValidationError("Fields name and ref must be different")

    # def write(self, vals):
    #     if 'age' in vals:
    #         self.appointment_ids


    # @api.onchange('age')
    # def generate_appointment(self):
    #     self.write({
    #         'appointment_ids': [(0, 0, {'name': "name 1"}), (0, 0, {'name': "name 2"})],
    #     })

    # api.depends()
    # api.onchange()
    # api.constrains()
    # api.model
    # api.returns 