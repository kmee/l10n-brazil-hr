# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest import mock

from esociallib.generator import _BUILDERS, _ensure_builders_loaded

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_br_hr_payroll.tests.common import cpf_valido

from .common import ESocialCicloCommon

BASE_MODULE = "odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario"


class _EventoGerado:
    """Saída simulada de um builder da esociallib."""

    def __init__(self, xml):
        self.xml = xml

    def to_xml(self):
        return self.xml


@tagged("post_install", "-at_install")
class TestBaseIntermediario(ESocialCicloCommon):
    """Comportamento comum dos intermediários e geração dos eventos."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Base = cls.env["l10n_br.esocial.base.intermediario"]
        cls.S1000 = cls.env["l10n_br.esocial.s1000"]

    def _s1000(self, **vals):
        return self.S1000.create(
            dict(
                {
                    "operacao": "inclusao",
                    "ini_valid": "2024-01",
                    "company_id": self.company.id,
                },
                **vals,
            )
        )

    def _builder_simulado(self, xml):
        """Troca o builder do S-1000 e simula a ausência dos XSDs oficiais."""
        _ensure_builders_loaded()
        builder = mock.Mock(return_value=_EventoGerado(xml))
        stack = mock.patch.dict(_BUILDERS, {"S-1000": builder})
        sem_xsd = mock.patch(
            f"{BASE_MODULE}.to_xml", side_effect=FileNotFoundError("xsd")
        )
        return stack, sem_xsd

    # -- Identificação do empregador ----------------------------------------

    def test_empregador_pessoa_fisica(self):
        cpf = cpf_valido(123456)
        empresa = self.env["res.company"].create({"name": "Empregador PF Teste"})
        empresa.partner_id.write({"vat": cpf, "is_company": False})
        intermediario = self.S1000.new({"company_id": empresa.id})
        self.assertEqual(
            intermediario._get_ide_empregador(), {"tp_insc": 2, "nr_insc": cpf}
        )

    def test_empregador_sem_inscricao(self):
        empresa = self.env["res.company"].create({"name": "Empregador Sem CNPJ"})
        intermediario = self.S1000.new({"company_id": empresa.id})
        with self.assertRaises(UserError) as erro:
            intermediario._get_ide_empregador()
        self.assertIn("Empregador Sem CNPJ", str(erro.exception))

    # -- Validações e utilitários -------------------------------------------

    def test_recibo_vazio_e_aceito(self):
        """A obrigatoriedade do recibo é de cada evento, não do formato."""
        self.assertIsNone(self.Base._validar_nr_recibo(False, "Recibo"))
        self.assertIsNone(
            self.Base._validar_nr_recibo(" 1.2.0000000000000012345 ", "Recibo")
        )

    def test_extrai_id_evento(self):
        casos = [
            ('<eSocial><evtX Id="ID1"/></eSocial>', "ID1"),
            ('<eSocial><Signature/><evtX Id="ID2"/></eSocial>', "ID2"),
            ('<evtX Id="ID3"/>', "ID3"),
            ("<eSocial><evtX/></eSocial>", False),
            (False, False),
        ]
        for xml, esperado in casos:
            with self.subTest(xml=xml):
                self.assertEqual(self.Base._extract_id_evento(xml), esperado)

    def test_base_abstrata_exige_implementacao(self):
        with self.assertRaises(NotImplementedError):
            self.Base._to_esociallib_dict()
        with self.assertRaises(NotImplementedError):
            self.Base._get_event_type()

    # -- Geração sem os XSDs oficiais ---------------------------------------

    def test_xml_malformado_nao_vira_evento(self):
        s1000 = self._s1000()
        builder, sem_xsd = self._builder_simulado("<eSocial><evtInfoEmpregador")
        with builder, sem_xsd, self.assertRaises(UserError) as erro:
            s1000.action_gerar_evento()
        self.assertIn("não é um XML válido", str(erro.exception))
        self.assertFalse(s1000.evento_id)
        self.assertFalse(
            self.env["l10n_br.esocial.evento"].search(
                [("origem_model", "=", s1000._name), ("origem_id", "=", s1000.id)]
            )
        )

    def test_xml_sem_id_gera_evento_sem_id(self):
        """Sem Id o evento é gerado, mas o retorno do lote não poderá casá-lo."""
        s1000 = self._s1000()
        xml = "<eSocial><evtInfoEmpregador/></eSocial>"
        builder, sem_xsd = self._builder_simulado(xml)
        with builder, sem_xsd:
            evento = s1000.action_gerar_evento()
        self.assertEqual(s1000.evento_id, evento)
        self.assertEqual(evento.tipo, "S-1000")
        self.assertFalse(evento.id_evento)
        self.assertEqual(evento.xml_envio, xml)

    # -- Campos opcionais dos eventos de tabela -----------------------------

    def test_s1000_cooperativa_construtora_e_fim_de_validade(self):
        self.company.write(
            {"l10n_br_esocial_ind_coop": "1", "l10n_br_esocial_ind_constr": "1"}
        )
        s1000 = self._s1000(operacao="alteracao", fim_valid="2024-12")
        data = s1000._to_esociallib_dict()
        self.assertEqual(data["ind_coop"], 1)
        self.assertEqual(data["ind_constr"], 1)
        self.assertEqual(data["fim_valid"], "2024-12")
        xml = s1000._gerar_xml()
        self.assertIn("<indCoop>1</indCoop>", xml)
        self.assertIn("<indConstr>1</indConstr>", xml)
        self.assertIn("<fimValid>2024-12</fimValid>", xml)

    def test_s1000_sem_cooperativa_nem_construtora(self):
        data = self._s1000()._to_esociallib_dict()
        self.assertNotIn("ind_coop", data)
        self.assertNotIn("ind_constr", data)
        self.assertNotIn("fim_valid", data)

    def test_s1010_exige_natureza_e_tipo(self):
        s1010 = self.env["l10n_br.esocial.s1010"].create(
            {
                "salary_rule_id": self.rule.id,
                "ini_valid": "2024-01",
                "fim_valid": "2024-12",
                "company_id": self.company.id,
            }
        )
        self.assertIn("<fimValid>2024-12</fimValid>", s1010._gerar_xml())
        self.rule.l10n_br_esocial_tp_rubr = False
        with self.assertRaises(UserError) as erro:
            s1010._to_esociallib_dict()
        self.assertIn("Tipo de Rubrica", str(erro.exception))
        self.rule.l10n_br_esocial_nat_rubr_id = False
        with self.assertRaises(UserError) as erro:
            s1010._to_esociallib_dict()
        self.assertIn("Natureza de Rubrica", str(erro.exception))

    # -- Rubricas do S-1200 e ações do holerite -----------------------------

    def test_s1200_so_informa_rubricas_do_esocial(self):
        payslip = self._criar_payslip(linhas=[("BASIC", 3000.0)])
        sem_natureza = self.rule.copy(
            {"code": "SEM_NAT", "l10n_br_esocial_nat_rubr_id": False}
        )
        sem_codigo = self.rule.copy(
            {"code": "SEM_COD", "l10n_br_esocial_cod_rubr": False}
        )
        for regra in sem_natureza | sem_codigo:
            self.env["hr.payslip.line"].create(
                {
                    "slip_id": payslip.id,
                    "salary_rule_id": regra.id,
                    "name": regra.code,
                    "code": regra.code,
                    "employee_id": self.employee.id,
                    "contract_id": self.contract.id,
                    "quantity": 1,
                    "amount": 100.0,
                    "rate": 100,
                }
            )
        s1200 = self.env["l10n_br.esocial.s1200"].create(
            {
                "employee_id": self.employee.id,
                "payslip_ids": [(6, 0, payslip.ids)],
                "per_apur": "2024-03",
                "ind_apuracao": "1",
                "company_id": self.company.id,
            }
        )
        self.assertEqual(
            s1200._build_itens_remun(),
            [{"cod_rubr": "SAL_BASE", "ide_tab_rubr": "1", "vr_rubr": "3000.0"}],
        )

    def test_holerite_em_rascunho_nao_gera_evento(self):
        payslip = self._criar_payslip(state="draft")
        with self.assertRaises(UserError):
            payslip.action_esocial_gerar_s1200()
        with self.assertRaises(UserError):
            payslip.action_esocial_gerar_s1210()
        self.assertFalse(payslip.l10n_br_esocial_s1200_id)

    def test_s1200_de_dois_trabalhadores_abre_lista(self):
        segundo = self.env["hr.employee"].create(
            {
                "name": "Segundo Trabalhador Ciclo eSocial",
                "vat": cpf_valido(654321),
                "l10n_br_esocial_matricula": "MAT002",
                "l10n_br_esocial_categoria_id": self.cat_101.id,
            }
        )
        contrato = self.env["hr.contract"].create(
            {
                "name": "Contrato Segundo Trabalhador",
                "employee_id": segundo.id,
                "wage": 2000.0,
                "date_start": "2024-01-02",
                "state": "open",
            }
        )
        primeiro_holerite = self._criar_payslip(linhas=[("BASIC", 3000.0)])
        segundo_holerite = self.env["hr.payslip"].create(
            {
                "name": "Holerite Segundo Trabalhador 03/2024",
                "employee_id": segundo.id,
                "contract_id": contrato.id,
                "date_from": "2024-03-01",
                "date_to": "2024-03-31",
                "state": "done",
            }
        )
        self.env["hr.payslip.line"].create(
            {
                "slip_id": segundo_holerite.id,
                "salary_rule_id": self.rule.id,
                "name": "BASIC",
                "code": "BASIC",
                "employee_id": segundo.id,
                "contract_id": contrato.id,
                "quantity": 1,
                "amount": 2000.0,
                "rate": 100,
            }
        )
        holerites = primeiro_holerite | segundo_holerite
        acao = holerites.action_esocial_gerar_s1200()
        eventos = self.env["l10n_br.esocial.evento"].search(acao["domain"])
        self.assertEqual(acao["view_mode"], "list,form")
        self.assertEqual(len(eventos), 2)
        self.assertEqual(set(eventos.mapped("tipo")), {"S-1200"})
        self.assertEqual(
            holerites.mapped("l10n_br_esocial_s1200_id.employee_id"),
            self.employee | segundo,
        )
