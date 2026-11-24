# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .constantes_rh import MESES


class L10nBrHrCaged(models.Model):
    """CAGED descontinuado.

    O CAGED foi extinto: desde janeiro de 2020 (Portaria SEPRT 1.127/2019)
    as movimentações são informadas pelo eSocial (S-2200 e S-2299), que
    alimenta o Novo CAGED. O modelo é mantido apenas para consulta do
    histórico já gerado: a ação de geração está bloqueada. O leiaute antigo
    do arquivo está no histórico do git (ver readme/ROADMAP.md).
    """

    _name = "l10n_br.hr.caged"
    _description = "CAGED - Cadastro de Empregados e Desempregados (descontinuado)"
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
        selection=MESES[:12],
        string="Mês",
        required=True,
    )
    ano = fields.Integer(
        required=True,
    )
    primeira_declaracao = fields.Boolean(
        string="Primeira Declaração",
        default=False,
    )
    responsavel = fields.Char(
        string="Responsável",
    )
    cpf_responsavel = fields.Char(
        string="CPF do Responsável",
        size=14,
    )
    email_responsavel = fields.Char(
        string="E-mail do Responsável",
    )
    contract_ids = fields.Many2many(
        comodel_name="hr.contract",
        string="Movimentações",
        readonly=True,
    )
    file_content = fields.Text(
        string="Conteúdo CAGED",
        readonly=True,
    )
    file_binary = fields.Binary(
        string="Arquivo CAGED",
        readonly=True,
    )
    file_name = fields.Char(
        string="Nome do Arquivo",
    )

    @api.depends("mes", "ano", "company_id")
    def _compute_name(self):
        for rec in self:
            mes_label = dict(MESES[:12]).get(rec.mes, "")
            rec.name = "CAGED {}/{} - {}".format(
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

    def action_gerar_caged(self):
        """Bloqueado: o CAGED foi extinto (ver docstring da classe)."""
        raise UserError(
            _(
                "O CAGED foi extinto e este gerador foi descontinuado.\n\n"
                "Norma: Portaria SEPRT 1.127/2019, que dispensou a declaração "
                "do CAGED para quem presta informações pelo eSocial. Desde "
                "janeiro de 2020 não há mais entrega do arquivo CAGED.\n\n"
                "Caminho atual: as admissões e os desligamentos são informados "
                "pelos eventos S-2200 (admissão) e S-2299 (desligamento) do "
                "eSocial, que alimentam o Novo CAGED.\n\n"
                "Os registros de CAGED já existentes continuam disponíveis "
                "somente para consulta de histórico."
            )
        )
