# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .constantes_rh import (
    CENTRALIZADORA,
    CODIGO_RECOLHIMENTO,
    MESES,
    MODALIDADE_ARQUIVO,
    RECOLHIMENTO_FGTS,
    RECOLHIMENTO_GPS,
)


class L10nBrHrSefip(models.Model):
    """SEFIP descontinuada.

    A SEFIP foi substituída pelo FGTS Digital (Portaria MTE 3.240/2023):
    desde a competência 03/2024 a guia (GFD) é emitida pelo FGTS Digital a
    partir dos eventos do eSocial, e a parte previdenciária passou para a
    DCTFWeb. O modelo é mantido apenas para consulta do histórico já
    gerado: a ação de geração está bloqueada. O leiaute antigo do arquivo
    está no histórico do git (ver readme/ROADMAP.md).
    """

    _name = "l10n_br.hr.sefip"
    _description = "SEFIP - FGTS e Previdência Social (descontinuada)"
    _order = "ano desc, mes desc"

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
    mes = fields.Selection(
        selection=MESES,
        string="Competência (Mês)",
        required=True,
    )
    ano = fields.Integer(
        string="Competência (Ano)",
        required=True,
    )
    codigo_recolhimento = fields.Selection(
        selection=CODIGO_RECOLHIMENTO,
        string="Código de Recolhimento",
        default="115",
        required=True,
    )
    modalidade_arquivo = fields.Selection(
        selection=MODALIDADE_ARQUIVO,
        string="Modalidade do Arquivo",
        default=" ",
    )
    recolhimento_fgts = fields.Selection(
        selection=RECOLHIMENTO_FGTS,
        string="Recolhimento FGTS",
        default="1",
    )
    recolhimento_gps = fields.Selection(
        selection=RECOLHIMENTO_GPS,
        string="Recolhimento GPS",
        default="1",
    )
    centralizadora = fields.Selection(
        selection=CENTRALIZADORA,
        string="Centralização",
        default="0",
    )
    codigo_fpas = fields.Char(
        string="Código FPAS",
        size=3,
        default="515",
    )
    codigo_outras_entidades = fields.Char(
        string="Código Outras Entidades",
        size=4,
    )
    payslip_ids = fields.Many2many(
        comodel_name="hr.payslip",
        string="Holerites",
        readonly=True,
    )
    file_content = fields.Text(
        string="Conteúdo SEFIP",
        readonly=True,
    )
    file_binary = fields.Binary(
        string="Arquivo SEFIP",
        readonly=True,
    )
    file_name = fields.Char(
        string="Nome do Arquivo",
    )

    @api.depends("mes", "ano", "company_id")
    def _compute_name(self):
        for rec in self:
            mes_label = dict(MESES).get(rec.mes, "")
            rec.name = "SEFIP {}/{} - {}".format(
                mes_label,
                rec.ano or "",
                rec.company_id.name or "",
            )

    def action_draft(self):
        self.write({"state": "draft"})

    def action_open(self):
        self.write({"state": "open"})

    def action_sent(self):
        self.write({"state": "sent"})

    def action_gerar_sefip(self):
        """Bloqueado: a SEFIP foi substituída (ver docstring da classe)."""
        raise UserError(
            _(
                "A SEFIP foi substituída pelo FGTS Digital e este gerador foi "
                "descontinuado.\n\n"
                "Norma: Portaria MTE 3.240/2023, que instituiu o FGTS Digital. "
                "Desde a competência 03/2024 o recolhimento do FGTS não usa "
                "mais o arquivo SEFIP nem a GRF.\n\n"
                "Caminho atual: os eventos de remuneração do eSocial alimentam "
                "o FGTS Digital, que emite a guia (GFD); as contribuições "
                "previdenciárias são confessadas e recolhidas pela DCTFWeb.\n\n"
                "Os registros de SEFIP já existentes continuam disponíveis "
                "somente para consulta de histórico."
            )
        )
