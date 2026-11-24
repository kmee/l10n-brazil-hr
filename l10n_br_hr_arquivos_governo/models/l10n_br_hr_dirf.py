# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrDirf(models.Model):
    """DIRF descontinuada.

    A obrigação foi extinta pela IN RFB 2.181/2024 (fatos a partir de
    01/01/2025 vão por EFD-Reinf/eSocial, com confissão e recolhimento na
    DCTFWeb). O modelo é mantido apenas para consulta do histórico já
    gerado: a ação de geração está bloqueada. O leiaute antigo do arquivo
    está no histórico do git (ver readme/ROADMAP.md).
    """

    _name = "l10n_br.hr.dirf"
    _description = "DIRF - Declaração do IR Retido na Fonte (descontinuada)"
    _order = "ano_referencia desc"

    name = fields.Char(
        string="Nome",
        compute="_compute_name",
        store=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Rascunho"),
            ("open", "Aberto"),
            ("sent", "Enviado"),
        ],
        default="draft",
        string="Situação",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    ano_referencia = fields.Integer(
        string="Ano de Referência",
        required=True,
    )
    ano_calendario = fields.Integer(
        string="Ano Calendário",
        required=True,
    )
    retificadora = fields.Boolean(
        string="Declaração Retificadora",
        default=False,
    )
    numero_recibo = fields.Char(
        string="Número do Recibo (retificação)",
    )
    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        string="Funcionários",
    )
    file_content = fields.Text(
        string="Conteúdo DIRF",
        readonly=True,
    )
    file_binary = fields.Binary(
        string="Arquivo DIRF",
        readonly=True,
    )
    file_name = fields.Char(
        string="Nome do Arquivo",
    )

    @api.depends("ano_referencia", "company_id")
    def _compute_name(self):
        for rec in self:
            rec.name = "DIRF {} - {}".format(
                rec.ano_referencia or "",
                rec.company_id.name or "",
            )

    def action_draft(self):
        self.write({"state": "draft"})

    def action_open(self):
        self.write({"state": "open"})

    def action_sent(self):
        self.write({"state": "sent"})

    def action_buscar_funcionarios(self):
        """Busca funcionários com holerites no ano de referência."""
        self.ensure_one()
        payslips = self.env["hr.payslip"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("date_from", ">=", "%d-01-01" % self.ano_calendario),
                ("date_from", "<=", "%d-12-31" % self.ano_calendario),
                ("state", "in", ["done", "paid"]),
            ]
        )
        employees = payslips.mapped("employee_id")
        self.employee_ids = employees
        return True

    def action_gerar_dirf(self):
        """Bloqueado: a DIRF foi extinta (ver docstring da classe)."""
        raise UserError(
            _(
                "A DIRF foi extinta e este gerador foi descontinuado.\n\n"
                "Norma: IN RFB 2.181/2024, que encerrou a DIRF. Para os fatos "
                "ocorridos a partir de 1o de janeiro de 2025 não há mais "
                "entrega de DIRF.\n\n"
                "Caminho atual: as retenções de imposto de renda na fonte são "
                "informadas pela EFD-Reinf (eventos da série R-4000) e pelo "
                "eSocial, e a confissão e o recolhimento passam pela DCTFWeb. "
                "O comprovante anual de rendimentos ao beneficiário continua "
                "devido e não depende deste gerador.\n\n"
                "Os registros de DIRF já existentes continuam disponíveis "
                "somente para consulta de histórico."
            )
        )
