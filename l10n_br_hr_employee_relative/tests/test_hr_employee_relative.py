# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestHrEmployeeRelative(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({"name": "Funcionária"})
        cls.relation = cls.env.ref("hr_employee_relative.relation_child")

    def _create_relative(self, **values):
        return self.env["hr.employee.relative"].create(
            {
                "employee_id": self.employee.id,
                "relation_id": self.relation.id,
                "name": "Dependente",
                **values,
            }
        )

    def test_indicators_are_stored_on_the_employee_relative(self):
        relative = self._create_relative(
            l10n_br_irrf_dependent=True,
            l10n_br_family_allowance=True,
            l10n_br_provision_amount=450.0,
        )
        self.assertIn(relative, self.employee.relative_ids)
        self.assertTrue(relative.l10n_br_irrf_dependent)
        self.assertTrue(relative.l10n_br_family_allowance)
        self.assertFalse(relative.l10n_br_alimony)
        self.assertEqual(relative.l10n_br_provision_amount, 450.0)
        self.assertEqual(relative.currency_id, self.employee.company_id.currency_id)

    def test_provision_amount_cannot_be_negative(self):
        with self.assertRaises(ValidationError):
            self._create_relative(l10n_br_provision_amount=-1.0)
