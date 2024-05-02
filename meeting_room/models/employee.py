from odoo import models, fields,api

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    partner_ids = fields.Many2one(
        "meeting.schedule",
        string="Attendees",
    )
    # @api.depends('company_id')
    # def replace_activity_user_id(self):
    #     if self.activity_user_id != None:
    #         self.company_id = self.activity_user_id