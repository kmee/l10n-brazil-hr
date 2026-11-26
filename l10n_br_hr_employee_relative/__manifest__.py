# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Dependentes do Funcionário - Brasil",
    "summary": "Indicadores de IRRF, salário-família, pensão e plano de saúde "
    "no dependente do funcionário",
    "version": "18.0.1.0.0",
    "development_status": "Beta",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/kmee/l10n-brazil-hr",
    "category": "Human Resources",
    "maintainers": ["mileo"],
    "depends": [
        "hr_employee_relative",
        "l10n_br_hr",
    ],
    "data": [
        "views/hr_employee_relative_views.xml",
    ],
    "demo": [
        "demo/hr_employee_relative_demo.xml",
    ],
    "installable": True,
}
