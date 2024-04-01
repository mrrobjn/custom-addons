from odoo import http

# import werkzeug
import json


class MyClass(http.Controller):

    @http.route('/check', auth ='public', type='http')
    def check(self):
        return "check ok"

    # @http.route("/check/<int:id>", auth="public", type="http")
    # def check(self,id):
    #     return "check ok " + str(id)

    # @http.route("/check", auth="public")
    # def check(self):
    #     return werkzeug.utils.redirect("https://www.google.com")

    # @http.route("/check", auth="public")
    # def check(self):
    #     return http.request.render("web.login")

    # @http.route("/check", auth="public", type="http")
    # def check(self):
    #     return json.dumps({"name": "dung"})

    # @http.route('/check', auth='public', type='http')
    # def check(self):
    #     partner = http.request.env['res.partner'].sudo().create({
    #         'name' : 'Mountain'
    #     })
    #     return 'Partner has been created'