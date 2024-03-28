from odoo import models, fields


class Player(models.Model):
    _name = "player"
    _description = "Player description"

    name = fields.Char(string="Name", required=True)
    image = fields.Binary(string="Image", attachment=True)
    gender = fields.Selection(
        [("male", "Male"), ("female", "Female")], string="Gender", default="male"
    )
    day_of_birth = fields.Datetime(
        string="Day of birth", groups="my_module.group_player_hr"
    )
