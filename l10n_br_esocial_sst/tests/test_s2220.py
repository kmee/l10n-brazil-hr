# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import unittest

from lxml import etree

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import HAS_ESOCIALLIB, EsocialSstCommon

NS_2220 = "http://www.esocial.gov.br/schema/evt/evtMonit/v_S_01_03_00"


@tagged("post_install", "-at_install")
class TestS2220(EsocialSstCommon):
    """RS-15: ASO transmitido pelo S-2220."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.medico = cls.env["l10n_br.sst.responsavel"].create(
            {
                "name": "Dra. Coordenadora",
                "cpf": "076.166.929-41",
                "ide_oc": "1",
                "nr_oc": "654321",
                "uf_oc": "MG",
            }
        )
        cls.pcmso = cls.env["l10n_br.sst.pcmso"].create(
            {
                "name": "PCMSO 2026",
                "medico_coordenador_id": cls.medico.id,
                "date_from": cls.hoje,
                "state": "vigente",
            }
        )
        cls.procedimento = cls.env["l10n_br.esocial.procedimento.diagnostico"].search(
            [], limit=1
        )

    def _aso_pendente(self, tipo="0"):
        exame = self.env["hr.employee.medical.examination"].l10n_br_gerar_aso(
            self.employee, tipo, date=self.hoje
        )
        self.env["l10n_br.sst.exame.complementar"].create(
            {
                "examination_id": exame.id,
                "procedimento_id": self.procedimento.id,
                "date": self.hoje,
                "ord_exame": "1",
                "ind_result": "1",
            }
        )
        exame.write(
            {
                "l10n_br_resultado": "1",
                "l10n_br_medico_nome": "Dr. Examinador",
                "l10n_br_crm": "123456",
                "l10n_br_uf_crm": "MG",
            }
        )
        return exame

    def _aso_concluido(self, tipo="0"):
        exame = self._aso_pendente(tipo)
        exame.to_done()
        return exame

    def test_concluir_aso_prepara_o_evento(self):
        exame = self._aso_concluido()
        self.assertTrue(exame.l10n_br_s2220_id)

    def test_nao_duplica_evento(self):
        exame = self._aso_concluido()
        primeiro = exame.l10n_br_s2220_id
        exame.action_gerar_s2220()
        self.assertEqual(exame.l10n_br_s2220_id, primeiro)

    def test_validacao_exige_exame_complementar(self):
        exame = self.env["hr.employee.medical.examination"].l10n_br_gerar_aso(
            self.employee, "0", date=self.hoje
        )
        exame.write(
            {
                "l10n_br_resultado": "1",
                "l10n_br_medico_nome": "Dr. Examinador",
            }
        )
        evento = self.env["l10n_br.esocial.s2220"].gerar_para_exame(exame)
        with self.assertRaises(UserError):
            evento._validar_antes_do_envio()

    def test_dicionario_do_evento(self):
        exame = self._aso_concluido()
        dados = exame.l10n_br_s2220_id._to_esociallib_dict()
        self.assertEqual(dados["tp_exame_ocup"], 0)
        self.assertEqual(dados["res_aso"], 1)
        self.assertEqual(dados["nm_med"], "Dr. Examinador")
        self.assertEqual(dados["nr_crm"], "123456")
        self.assertEqual(len(dados["exames"]), 1)
        self.assertEqual(dados["nm_resp"], "Dra. Coordenadora")

    def test_demissional_usa_o_codigo_nove(self):
        """O leiaute usa 9 para o demissional, e não 8."""
        exame = self._aso_concluido(tipo="9")
        dados = exame.l10n_br_s2220_id._to_esociallib_dict()
        self.assertEqual(dados["tp_exame_ocup"], 9)

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_xml_do_evento(self):
        exame = self._aso_concluido()
        xml = exame.l10n_br_s2220_id._gerar_xml()
        root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
        ns = {"e": NS_2220}
        self.assertEqual(root.find(".//e:exMedOcup/e:tpExameOcup", ns).text, "0")
        self.assertEqual(root.find(".//e:aso/e:resAso", ns).text, "1")
        self.assertEqual(root.find(".//e:medico/e:nmMed", ns).text, "Dr. Examinador")

    def test_medico_conclui_aso_e_gera_o_evento(self):
        """A saúde ocupacional conclui o ASO sem precisar do perfil de gestor."""
        grupo = self.env.ref("l10n_br_hr_sst_aso.group_sst_medico")
        medico = self.env["res.users"].create(
            {
                "name": "Medico S-2220",
                "login": "medico_s2220",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id, grupo.id])],
            }
        )
        exame = self.env["hr.employee.medical.examination"].l10n_br_gerar_aso(
            self.employee, "1", date=self.hoje
        )
        exame.write(
            {
                "l10n_br_resultado": "1",
                "l10n_br_medico_nome": "Dr. Examinador",
            }
        )
        exame.with_user(medico).to_done()
        self.assertTrue(exame.l10n_br_s2220_id)

    def test_validacao_lista_os_campos_faltando(self):
        exame = self.env["hr.employee.medical.examination"].create(
            {"name": "ASO incompleto", "employee_id": self.employee.id}
        )
        evento = self.env["l10n_br.esocial.s2220"].gerar_para_exame(exame)
        with self.assertRaises(UserError) as erro:
            evento._validar_antes_do_envio()
        mensagem = str(erro.exception)
        for rotulo in (
            "tipo de ASO",
            "data do ASO",
            "nome do médico emitente",
            "ao menos um exame complementar",
        ):
            self.assertIn(rotulo, mensagem)

    def test_concluir_aso_mantem_o_evento_ja_gerado(self):
        exame = self._aso_pendente()
        acao = exame.action_gerar_s2220()
        evento = exame.l10n_br_s2220_id
        self.assertEqual(acao["res_id"], evento.id)
        exame.to_done()
        self.assertEqual(exame.l10n_br_s2220_id, evento)
        self.assertEqual(
            self.env["l10n_br.esocial.s2220"].search_count(
                [("examination_id", "=", exame.id)]
            ),
            1,
        )

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_sem_resultado_crm_nem_coordenador(self):
        """resAso, nrCRM, ufCRM e respMonit são opcionais no leiaute."""
        exame = self._aso_pendente()
        exame.write(
            {
                "l10n_br_resultado": False,
                "l10n_br_crm": False,
                "l10n_br_uf_crm": False,
                "l10n_br_pcmso_id": False,
            }
        )
        exame.action_gerar_s2220()
        evento = exame.l10n_br_s2220_id
        dados = evento._to_esociallib_dict()
        self.assertEqual(dados["nm_med"], "Dr. Examinador")
        for chave in ("res_aso", "nr_crm", "uf_crm", "cpf_resp", "nm_resp"):
            self.assertNotIn(chave, dados)
        xml = evento._gerar_xml()
        root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
        ns = {"e": NS_2220}
        self.assertIsNone(root.find(".//e:aso/e:resAso", ns))
        self.assertIsNone(root.find(".//e:medico/e:nrCRM", ns))
        self.assertIsNone(root.find(".//e:respMonit", ns))

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_gerar_evento_valida_antes(self):
        incompleto = self.env["hr.employee.medical.examination"].create(
            {"name": "ASO incompleto", "employee_id": self.employee.id}
        )
        evento = self.env["l10n_br.esocial.s2220"].gerar_para_exame(incompleto)
        with self.assertRaisesRegex(UserError, "exame complementar"):
            evento.action_gerar_evento()
        self.assertFalse(evento.evento_id)
        exame = self._aso_concluido()
        registro = exame.l10n_br_s2220_id.action_gerar_evento()
        self.assertEqual(registro.tipo, "S-2220")
        self.assertTrue(registro.id_evento)
        self.assertEqual(exame.l10n_br_s2220_id.evento_id, registro)
