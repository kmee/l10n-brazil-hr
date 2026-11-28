# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrEmployeeRelative(models.Model):
    _inherit = "hr.employee.relative"

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="employee_id.company_id.currency_id",
    )
    l10n_br_irrf_dependent = fields.Boolean(
        string="Dependente para IRRF",
        help="Pode ser deduzido da base de cálculo do IRRF do funcionário.",
    )
    l10n_br_family_allowance = fields.Boolean(
        string="Dependente do salário-família",
        help="Dá direito à cota de salário-família.",
    )
    l10n_br_alimony = fields.Boolean(
        string="Pensão alimentícia",
        help="O funcionário paga pensão alimentícia a este dependente.",
    )
    l10n_br_incapable_of_work = fields.Boolean(
        string="Incapaz para o trabalho",
    )
    l10n_br_health_plan = fields.Boolean(
        string="Plano de saúde",
        help="O dependente está coberto pelo plano de saúde do funcionário.",
    )
    l10n_br_provision_amount = fields.Monetary(
        string="Valor de provisão",
        currency_field="currency_id",
        help="Valor da pensão ou provisão destinada ao dependente.",
    )
    l10n_br_incapacity_proof = fields.Binary(
        string="Comprovante de incapacidade",
    )
    l10n_br_incapacity_proof_name = fields.Char()
    l10n_br_document = fields.Binary(
        string="Documento do dependente",
    )
    l10n_br_document_name = fields.Char()

    @api.constrains("l10n_br_provision_amount")
    def _check_l10n_br_provision_amount(self):
        for relative in self:
            if relative.l10n_br_provision_amount < 0:
                raise ValidationError(
                    self.env._("O valor de provisão não pode ser negativo.")
                )
