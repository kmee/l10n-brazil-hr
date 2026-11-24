# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import unittest

from lxml import etree

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import HAS_ESOCIALLIB, EsocialSstCommon

NS_2221 = "http://www.esocial.gov.br/schema/evt/evtToxic/v_S_01_03_00"
NS_2240 = "http://www.esocial.gov.br/schema/evt/evtExpRisco/v_S_01_03_00"
RECIBO = "1.1.1234567890123456789"


@tagged("post_install", "-at_install")
class TestBaseSst(EsocialSstCommon):
    """ideEvento e ideVinculo, comuns aos eventos de SST."""

    def _s2221(self, **kwargs):
        valores = {
            "company_id": self.company.id,
            "employee_id": self.employee.id,
            "dt_exame": self.hoje,
            "cnpj_lab": "12.345.678/0001-99",
            "cod_seq_exame": "AB123456789",
            "nm_med": "Dr. Toxicologista",
        }
        valores.update(kwargs)
        return self.env["l10n_br.esocial.s2221"].create(valores)

    @staticmethod
    def _xml(evento):
        xml = evento._gerar_xml()
        return etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)

    def test_trabalhador_sem_cpf(self):
        evento = self._s2221()
        self.employee.vat = False
        with self.assertRaisesRegex(UserError, "não possui CPF"):
            evento._to_esociallib_dict()

    def test_sem_matricula_nem_categoria(self):
        """ideVinculo/codCateg é obrigatório se não houver matrícula."""
        self._entrega_epi()
        evento = self.env["l10n_br.esocial.s2240"].gerar_para_contrato(
            self.contract, data=self.hoje
        )
        self.employee.write(
            {
                "l10n_br_esocial_matricula": False,
                "l10n_br_esocial_categoria_id": False,
            }
        )
        with self.assertRaisesRegex(UserError, "nem a categoria"):
            evento._to_esociallib_dict()

    def test_retificacao_exige_recibo(self):
        evento = self._s2221(ind_retif="2")
        with self.assertRaisesRegex(UserError, "recibo do evento retificado"):
            evento._to_esociallib_dict()
        evento.nr_recibo = RECIBO
        dados = evento._to_esociallib_dict()
        self.assertEqual(dados["ind_retif"], 2)
        self.assertEqual(dados["nr_recibo"], RECIBO)

    def test_evento_original_nao_leva_recibo(self):
        dados = self._s2221(nr_recibo=RECIBO)._to_esociallib_dict()
        self.assertEqual(dados["ind_retif"], 1)
        self.assertNotIn("nr_recibo", dados)

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_xml_da_retificacao(self):
        evento = self._s2221(ind_retif="2", nr_recibo=RECIBO)
        ns = {"e": NS_2221}
        ide_evento = self._xml(evento).find(".//e:ideEvento", ns)
        self.assertEqual(ide_evento.find("e:indRetif", ns).text, "2")
        self.assertEqual(ide_evento.find("e:nrRecibo", ns).text, RECIBO)

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_sem_matricula_usa_a_categoria(self):
        """Trabalhador sem vínculo (TSVE) se identifica pela categoria."""
        self._entrega_epi()
        evento = self.env["l10n_br.esocial.s2240"].gerar_para_contrato(
            self.contract, data=self.hoje
        )
        self.employee.l10n_br_esocial_matricula = False
        dados = evento._to_esociallib_dict()
        self.assertEqual(dados["cod_categ"], "101")
        self.assertNotIn("matricula", dados)
        ns = {"e": NS_2240}
        ide_vinculo = self._xml(evento).find(".//e:ideVinculo", ns)
        self.assertEqual(ide_vinculo.find("e:codCateg", ns).text, "101")
        self.assertIsNone(ide_vinculo.find("e:matricula", ns))
