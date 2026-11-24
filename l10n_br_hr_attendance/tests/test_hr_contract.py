# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Testes da dispensa de controle de jornada (art. 62 da CLT)."""

from datetime import date

from odoo.tests import tagged

from .common import PontoCommon


@tagged("post_install", "-at_install")
class TestHrContract(PontoCommon):
    def test_contrato_dispensado_fica_fora_do_controle(self):
        """Art. 62 da CLT: contrato dispensado não tem jornada apurada."""
        Contrato = self.env["hr.contract"]
        controlado = Contrato.create(
            {
                "name": "Contrato com controle",
                "employee_id": self.employee.id,
                "wage": 3000.0,
                "date_start": date(2026, 1, 1),
            }
        )
        gerente = self.env["hr.employee"].create({"name": "Gerente Geral"})
        dispensado = Contrato.create(
            {
                "name": "Contrato de gestão",
                "employee_id": gerente.id,
                "wage": 9000.0,
                "date_start": date(2026, 1, 1),
                "l10n_br_dispensado_controle_jornada": True,
                "l10n_br_motivo_dispensa_jornada": "gestao",
            }
        )
        self.assertEqual(
            (controlado | dispensado)._l10n_br_sujeito_controle_jornada(),
            controlado,
        )
