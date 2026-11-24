# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: escolha do diário de folha e mapeamento regra->conta por empresa.

Cobertura:
  - diário com código FOPAG de outra empresa é o diário de folha dela;
  - contrato de empresa sem diário nenhum mantém o diário original;
  - empresa sem plano de contas: nenhuma conta encontrada e o mapeamento é
    adiado, sem tocar nas regras;
  - mapeamento pedido para empresa que não é dona do FOPAG não altera o
    diário nem as contas já configuradas;
  - rotina da demo vincula ao FOPAG os holerites em rascunho da empresa dona
    do diário e calcula-os, sem mexer nos de outra empresa.
"""

from datetime import date

from odoo.tests import tagged

from odoo.addons.l10n_br_hr_payroll.tests.common import PayrollCommon


@tagged("post_install", "-at_install")
class TestDiarioEMapeamento(PayrollCommon):
    """Diário de folha e mapeamento contábil fora da empresa principal."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Journal = cls.env["account.journal"]
        cls.SalaryRule = cls.env["hr.salary.rule"]
        cls.fopag = cls.env.ref("l10n_br_hr_payroll_account.journal_folha_pagamento")
        cls.rule_salario = cls.env.ref("l10n_br_hr_payroll.hr_rule_salario_base")
        cls.rule_net = cls.env.ref("l10n_br_hr_payroll.hr_rule_net")
        cls.outra = cls.env["res.company"].create({"name": "Empresa Teste Sem Plano"})

    def test_diario_fopag_da_outra_empresa_pelo_codigo(self):
        """O FOPAG do módulo é de outra empresa: vale o diário FOPAG dela."""
        fopag_outra = self.Journal.create(
            {
                "name": "Folha (Empresa Teste)",
                "code": "FOPAG",
                "type": "general",
                "company_id": self.outra.id,
            }
        )
        self.Journal.create(
            {
                "name": "Diversos (Empresa Teste)",
                "code": "TSTD",
                "type": "general",
                "company_id": self.outra.id,
            }
        )
        self.assertNotEqual(self.fopag.company_id, self.outra)
        self.assertEqual(
            self.Journal.with_company(self.outra)._l10n_br_payroll_journal(),
            fopag_outra,
        )

    def test_contrato_de_empresa_sem_diario_mantem_o_original(self):
        """Sem diário na empresa do contrato, o diário padrão é mantido."""
        self.assertFalse(self.Journal.search([("company_id", "=", self.outra.id)]))
        emp = self.env["hr.employee"].create(
            {
                "name": "Empregado Empresa Sem Diário",
                "company_id": self.outra.id,
                "l10n_br_tipo_contrato": "clt",
            }
        )
        contract = self.env["hr.contract"].create(
            {
                "name": "Contrato Empresa Sem Diário",
                "employee_id": emp.id,
                "wage": 3000.00,
                "date_start": date(2024, 1, 1),
                "struct_id": self.structure_clt.id,
                "company_id": self.outra.id,
            }
        )
        self.assertEqual(contract.journal_id, self.fopag)

    def test_empresa_sem_plano_de_contas_adia_o_mapeamento(self):
        """Sem conta de despesa e de passivo, nada é vinculado."""
        self.assertFalse(
            self.SalaryRule._l10n_br_find_account(self.outra, "expense_salarios")
        )
        self.assertFalse(self.SalaryRule._l10n_br_find_account(self.outra, "liability"))
        debito = self.rule_salario.account_debit
        self.assertFalse(self.SalaryRule._l10n_br_setup_payroll_accounts(self.outra))
        self.assertEqual(self.rule_salario.account_debit, debito)

    def test_mapeamento_de_outra_empresa_nao_altera_o_fopag(self):
        """Pedir o mapeamento para empresa que não é dona do FOPAG não troca
        a empresa nem a conta padrão do diário, nem as contas já mapeadas."""
        Account = self.env["account.account"].with_company(self.outra)
        despesa = Account.create(
            {
                "name": "Salários (Empresa Teste)",
                "code": "0TST61",
                "account_type": "expense",
                "company_ids": [(6, 0, self.outra.ids)],
            }
        )
        Account.create(
            {
                "name": "Salários a Pagar (Empresa Teste)",
                "code": "0TST21",
                "account_type": "liability_current",
                "company_ids": [(6, 0, self.outra.ids)],
            }
        )
        self.assertEqual(
            self.SalaryRule._l10n_br_find_account(self.outra, "expense_salarios"),
            despesa,
        )
        empresa = self.fopag.company_id
        conta_padrao = self.fopag.default_account_id
        debito = self.rule_salario.account_debit
        credito = self.rule_net.account_credit
        self.assertTrue(self.SalaryRule._l10n_br_setup_payroll_accounts(self.outra))
        self.assertEqual(self.fopag.company_id, empresa)
        self.assertEqual(self.fopag.default_account_id, conta_padrao)
        self.assertEqual(self.rule_salario.account_debit, debito)
        self.assertEqual(self.rule_net.account_credit, credito)

    def test_demo_vincula_rascunhos_ao_fopag(self):
        """A rotina da demo leva ao FOPAG os rascunhos da empresa dona do
        diário e os calcula; holerite de outra empresa fica no próprio."""
        empresa = self.fopag.company_id
        outro_diario = self.Journal.create(
            {
                "name": "Diário Avulso (teste)",
                "code": "TSTA",
                "type": "general",
                "company_id": empresa.id,
            }
        )
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        contract.journal_id = outro_diario
        payslip = self.env["hr.payslip"].create(
            {
                "name": f"Holerite - {emp.name}",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": contract.struct_id.id,
                "date_from": date(2024, 3, 1),
                "date_to": date(2024, 3, 31),
                "company_id": empresa.id,
            }
        )
        self.assertEqual(payslip.journal_id, outro_diario)
        self.assertFalse(payslip.line_ids)

        diario_outra = self.Journal.create(
            {
                "name": "Folha (Empresa Teste)",
                "code": "TSTF",
                "type": "general",
                "company_id": self.outra.id,
            }
        )
        emp_outra = self.env["hr.employee"].create(
            {
                "name": "Empregado Empresa Teste",
                "company_id": self.outra.id,
                "l10n_br_tipo_contrato": "clt",
            }
        )
        contract_outra = self.env["hr.contract"].create(
            {
                "name": "Contrato Empresa Teste",
                "employee_id": emp_outra.id,
                "wage": 3000.00,
                "date_start": date(2024, 1, 1),
                "struct_id": self.structure_clt.id,
                "company_id": self.outra.id,
            }
        )
        self.assertEqual(contract_outra.journal_id, diario_outra)
        # Estrutura sem regras: o cálculo da demo roda em todas as empresas, e
        # o que importa aqui é só o diário deste holerite.
        estrutura_vazia = self.env["hr.payroll.structure"].create(
            {
                "name": "Estrutura vazia (teste)",
                "code": "TST_VAZIA",
                "parent_id": False,
                "company_id": self.outra.id,
            }
        )
        payslip_outra = self.env["hr.payslip"].create(
            {
                "name": "Holerite Empresa Teste",
                "employee_id": emp_outra.id,
                "contract_id": contract_outra.id,
                "struct_id": estrutura_vazia.id,
                "date_from": date(2024, 3, 1),
                "date_to": date(2024, 3, 31),
                "company_id": self.outra.id,
            }
        )

        self.env["hr.payslip"]._demo_compute_payslips()

        self.assertEqual(payslip.journal_id, self.fopag)
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "SALARIO_BASE"), 3000.0
        )
        self.assertEqual(payslip_outra.journal_id, diario_outra)

        # Rodar de novo não tem o que corrigir: tudo já está no FOPAG.
        self.env["hr.payslip"]._demo_compute_payslips()
        self.assertEqual(payslip.journal_id, self.fopag)
        self.assertEqual(payslip_outra.journal_id, diario_outra)
