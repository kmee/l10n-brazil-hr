# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: casos-limite de férias, avos e alocação.

Cobertura:
  - holerite de férias sem alocação e sem abono (caminho legado): 30 dias
    gozados e nenhum vendido; o fracionamento (RF-19) não se aplica;
  - dias negativos e soma de frações acima do direito (CLT art. 130);
  - avos de 13º e de férias zerados em holerite sem contrato;
  - avos de férias quando o aniversário de admissão do ano ainda não chegou
    (CLT art. 146 parágrafo único: fração superior a 14 dias conta um avo);
  - alocação de outro tipo de ausência não recebe os dias de direito das
    férias (CLT art. 130 vale só para o tipo Férias);
  - período aquisitivo vencido e já pago por inteiro sai das férias vencidas
    da rescisão (CLT art. 146).
"""

from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.l10n_br_hr_payroll.tests.common import cpf_valido

from .common import VacationCommon


@tagged("post_install", "-at_install")
class TestCasosLimiteFerias(VacationCommon):
    """Caminhos de borda de férias, avos e alocação."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.emp = cls.env["hr.employee"].create(
            {
                "name": "Empregado Casos-Limite",
                "l10n_br_tipo_contrato": "clt",
                "vat": cpf_valido(990001),
                "company_id": cls.env.company.id,
            }
        )
        cls.contract = cls.env["hr.contract"].create(
            {
                "name": "Contrato Casos-Limite",
                "employee_id": cls.emp.id,
                "wage": 3000.00,
                "date_start": date(2023, 6, 10),
                "state": "open",
                "struct_id": cls.structure_clt.id,
                "company_id": cls.env.company.id,
            }
        )
        cls.alloc = cls.env["hr.leave.allocation"].create(
            {
                "employee_id": cls.emp.id,
                "holiday_status_id": cls.leave_type_ferias.id,
                "date_from": date(2023, 6, 10),
                "date_to": date(2024, 6, 9),
            }
        )
        cls.alloc.action_validate()

    def _ferias(self, **vals):
        dados = {
            "name": "Férias Casos-Limite",
            "employee_id": self.emp.id,
            "contract_id": self.contract.id,
            "struct_id": self.structure_ferias.id,
            "date_from": date(2024, 7, 1),
            "date_to": date(2024, 7, 31),
            "company_id": self.env.company.id,
        }
        dados.update(vals)
        return self.env["hr.payslip"].create(dados)

    def _rescisao(self, date_from, date_to, **vals):
        dados = {
            "name": "Rescisão Casos-Limite",
            "employee_id": self.emp.id,
            "contract_id": self.contract.id,
            "struct_id": self.structure_rescisao.id,
            "date_from": date_from,
            "date_to": date_to,
            "l10n_br_tipo_rescisao": "pedido_demissao",
            "l10n_br_aviso_previo": "nao_aplicavel",
            "company_id": self.env.company.id,
        }
        dados.update(vals)
        return self.env["hr.payslip"].create(dados)

    def test_ferias_sem_alocacao_e_sem_abono(self):
        """Caminho legado sem abono: 30 dias gozados, nenhum vendido, e os
        dias de fração digitados não acionam a validação do fracionamento."""
        payslip = self._ferias()
        self.assertEqual(payslip.l10n_br_dias_ferias_gozadas, 30)
        self.assertEqual(payslip.l10n_br_dias_ferias_vendidas, 0)
        self.assertEqual(payslip.l10n_br_dias_direito_ferias, 0.0)
        # Sem alocação a regra do art. 134 §1º não se aplica: 4 dias numa
        # fração seria recusado com alocação, aqui é só gravado.
        payslip.write({"l10n_br_dias_periodo_gozado": 4})
        self.assertEqual(payslip.l10n_br_dias_periodo_gozado, 4)
        self.assertEqual(payslip.l10n_br_dias_ferias_gozadas, 30)

    def test_dias_negativos_recusados(self):
        """Dias de abono negativos não passam pela validação."""
        with self.assertRaisesRegex(ValidationError, "não podem ser negativos"):
            self._ferias(
                l10n_br_ferias_allocation_id=self.alloc.id,
                l10n_br_dias_periodo_gozado=20,
                l10n_br_dias_abono=-1,
            )

    def test_soma_das_fracoes_acima_do_direito(self):
        """22 gozados + 10 vendidos (32) supera os 30 dias de direito, mesmo
        com o abono dentro de 1/3 do direito (CLT art. 130 e 143)."""
        with self.assertRaisesRegex(ValidationError, r"\(32\) supera os 30"):
            self._ferias(
                l10n_br_ferias_allocation_id=self.alloc.id,
                l10n_br_dias_periodo_gozado=22,
                l10n_br_dias_abono=10,
            )

    def test_holerite_sem_contrato_nao_tem_avos(self):
        """Sem contrato não há data de admissão: avos e aviso prévio zerados,
        e a rescisão não é projetada pelo aviso."""
        payslip = self._rescisao(
            date(2024, 3, 1),
            date(2024, 3, 31),
            contract_id=False,
            struct_id=False,
            l10n_br_tipo_rescisao="sem_justa_causa",
            l10n_br_aviso_previo="indenizado",
        )
        self.assertFalse(payslip.contract_id)
        self.assertEqual(payslip.l10n_br_avos_13, 0)
        self.assertEqual(payslip.l10n_br_avos_ferias, 0)
        self.assertEqual(payslip._l10n_br_dias_aviso_previo(), 0)
        self.assertEqual(payslip._l10n_br_data_projetada_rescisao(), date(2024, 3, 31))

    def test_avos_ferias_antes_do_aniversario_de_admissao(self):
        """Admissão em 10/06/2023, desligamento em 31/03/2024 (pedido de
        demissão, sem projeção): o período em curso começa em 10/06/2023.
        São 9 meses inteiros mais 22 dias (10/03 a 31/03), fração superior
        a 14 dias que conta mais um avo (CLT art. 146 parágrafo único)."""
        payslip = self._rescisao(date(2024, 3, 1), date(2024, 3, 31))
        self.assertEqual(payslip.l10n_br_avos_ferias, 10)

    def test_alocacao_de_outro_tipo_nao_usa_dias_de_ferias(self):
        """Alocação de outro tipo de ausência mantém os dias informados,
        mesmo com faltas registradas: a tabela do art. 130 é só das férias."""
        tipo = self.env["hr.leave.type"].create({"name": "Licença de teste"})
        alloc = self.env["hr.leave.allocation"].create(
            {
                "employee_id": self.emp.id,
                "holiday_status_id": tipo.id,
                "number_of_days": 5,
                "date_from": date(2024, 1, 1),
                "date_to": date(2024, 12, 31),
            }
        )
        self.assertEqual(alloc.number_of_days, 5)
        alloc.write({"l10n_br_faltas_periodo_aquisitivo": 10})
        self.assertEqual(alloc.number_of_days, 5)

    def test_periodo_vencido_pago_sai_das_ferias_vencidas(self):
        """Período aquisitivo vencido entra nas férias vencidas da rescisão
        enquanto não é pago; depois de confirmado o holerite que gozou os 30
        dias, não resta saldo (CLT art. 146)."""
        rescisao = self._rescisao(date(2024, 9, 1), date(2024, 9, 30))
        ferias = self._ferias(
            l10n_br_ferias_allocation_id=self.alloc.id,
            l10n_br_dias_periodo_gozado=30,
        )
        self.assertEqual(
            rescisao._l10n_br_ferias_vencidas_dados(),
            [{"dias": 30.0, "dobro": False}],
        )
        ferias.compute_sheet()
        ferias.action_payslip_done()
        self.assertEqual(ferias.state, "done")
        self.assertEqual(rescisao._l10n_br_ferias_vencidas_dados(), [])
