# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import unittest
from datetime import date

from lxml import etree

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import HAS_ESOCIALLIB, EsocialSstCommon

NS_2210 = "http://www.esocial.gov.br/schema/evt/evtCAT/v_S_01_03_00"


@tagged("post_install", "-at_install")
class TestS2210(EsocialSstCommon):
    """RS-14: CAT transmitida pelo S-2210."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.acidente = cls.env["l10n_br.sst.acidente"].create(
            {
                "employee_id": cls.employee.id,
                "date_acidente": date(2026, 6, 10),
                "hora_acidente": "1430",
                "hrs_trab_antes_acid": "0330",
                "tp_acid": "1",
                "situacao_geradora_id": cls.env["l10n_br.esocial.situacao.geradora"]
                .search([], limit=1)
                .id,
                "parte_corpo_id": cls.env["l10n_br.esocial.parte.corpo"]
                .search([], limit=1)
                .id,
                "agente_causador_id": cls.env["l10n_br.esocial.agente.causador"]
                .search([], limit=1)
                .id,
                "natureza_lesao_id": cls.env["l10n_br.esocial.natureza.lesao"]
                .search([], limit=1)
                .id,
                "cid_id": cls.env["l10n_br.esocial.cid"].search([], limit=1).id,
                "dsc_lograd": "RUA DAS FLORES",
                "nr_lograd": "100",
                "bairro_local": "CENTRO",
                "cep_local": "37500000",
                "date_atendimento": date(2026, 6, 10),
                "hora_atendimento": "1500",
                "dur_trat": 15,
                "nm_emit": "Dr. Plantonista",
                "ide_oc_emit": "1",
                "nr_oc_emit": "123456",
                "uf_oc_emit": "MG",
                "houve_afastamento": True,
                "ind_afast": "S",
                "ultimo_dia_trabalhado": date(2026, 6, 10),
            }
        )
        cls.acidente.action_registrar()
        cls.cat = cls.acidente.cat_ids

    def test_emitir_prepara_o_evento(self):
        self.cat.action_emitir()
        self.assertTrue(self.cat.s2210_id)
        self.assertEqual(self.cat.s2210_id.employee_id, self.employee)

    def test_validacao_exige_atestado(self):
        self.acidente.nm_emit = False
        evento = self.cat.action_gerar_s2210()
        with self.assertRaises(UserError):
            evento._validar_antes_do_envio()

    def test_tipica_exige_horas_trabalhadas(self):
        evento = self.cat.action_gerar_s2210()
        self.acidente.hrs_trab_antes_acid = False
        with self.assertRaisesRegex(UserError, "hrsTrabAntesAcid"):
            evento._validar_antes_do_envio()
        self.acidente.hrs_trab_antes_acid = "2530"
        evento._validar_antes_do_envio()

    def test_trajeto_exige_horas_trabalhadas(self):
        evento = self.cat.action_gerar_s2210()
        self.acidente.write({"tp_acid": "3", "hrs_trab_antes_acid": False})
        with self.assertRaisesRegex(UserError, "hrsTrabAntesAcid"):
            evento._validar_antes_do_envio()
        self.acidente.hrs_trab_antes_acid = "0330"
        evento._validar_antes_do_envio()

    def test_trajeto_antes_de_20_07_2022_dispensa_horas_trabalhadas(self):
        """Só o trajeto tem marco de data no leiaute; a típica sempre exige."""
        evento = self.cat.action_gerar_s2210()
        self.acidente.write(
            {
                "tp_acid": "3",
                "date_acidente": date(2022, 7, 19),
                "hrs_trab_antes_acid": False,
            }
        )
        evento._validar_antes_do_envio()
        self.acidente.tp_acid = "1"
        with self.assertRaisesRegex(UserError, "hrsTrabAntesAcid"):
            evento._validar_antes_do_envio()

    def test_doenca_recusa_horas_trabalhadas(self):
        evento = self.cat.action_gerar_s2210()
        self.acidente.write({"tp_acid": "2", "hrs_trab_antes_acid": False})
        evento._validar_antes_do_envio()
        with self.assertRaises(ValidationError):
            self.acidente.hrs_trab_antes_acid = "0300"

    def test_reabertura_sem_recibo_de_origem(self):
        self.cat.action_emitir()
        reabertura = self.acidente._criar_cat("2")
        reabertura.nr_rec_cat_orig = False
        evento = reabertura.action_gerar_s2210()
        with self.assertRaises(UserError):
            evento._validar_antes_do_envio()

    def test_dicionario_do_evento(self):
        evento = self.cat.action_gerar_s2210()
        dados = evento._to_esociallib_dict()
        self.assertEqual(dados["dt_acid"], "2026-06-10")
        self.assertEqual(dados["hr_acid"], "1430")
        self.assertEqual(dados["hrs_trab_antes_acid"], "0330")
        self.assertEqual(dados["tp_acid"], 1)
        self.assertEqual(dados["tp_cat"], 1)
        self.assertEqual(dados["ind_cat_obito"], "N")
        self.assertEqual(dados["houve_afast"], "S")
        self.assertEqual(dados["nm_emit"], "Dr. Plantonista")
        self.assertEqual(dados["cpf_trab"], "07616692990")

    def test_obito_leva_data_do_obito(self):
        self.acidente.write({"houve_obito": True, "date_obito": date(2026, 6, 11)})
        evento = self.cat.action_gerar_s2210()
        dados = evento._to_esociallib_dict()
        self.assertEqual(dados["ind_cat_obito"], "S")
        self.assertEqual(dados["dt_obito"], "2026-06-11")

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_xml_do_evento(self):
        evento = self.cat.action_gerar_s2210()
        xml = evento._gerar_xml()
        root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
        ns = {"e": NS_2210}
        self.assertEqual(root.find(".//e:cat/e:dtAcid", ns).text, "2026-06-10")
        self.assertEqual(root.find(".//e:cat/e:tpCat", ns).text, "1")
        self.assertEqual(
            root.find(".//e:emitente/e:nmEmit", ns).text, "Dr. Plantonista"
        )

    def test_recibo_volta_para_a_cat(self):
        """O recibo do eSocial chega à CAT e libera a CAT de reabertura."""
        self.cat.action_emitir()
        evento = self.env["l10n_br.esocial.evento"].create(
            {"tipo": "S-2210", "company_id": self.cat.company_id.id}
        )
        evento.registrar_aceite(nr_recibo="1.1.1234567890123456789")
        self.cat.s2210_id.evento_id = evento
        self.env["l10n_br.sst.cat"]._atualizar_recibo()
        self.assertEqual(self.cat.state, "transmitida")
        self.assertEqual(self.cat.numero_recibo, "1.1.1234567890123456789")
        reabertura = self.acidente._criar_cat("2")
        self.assertEqual(reabertura.nr_rec_cat_orig, "1.1.1234567890123456789")

    # Grupos opcionais do local, do atestado e da CAT de origem

    def _xml(self, evento):
        xml = evento._gerar_xml()
        return etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)

    def _cidade(self):
        return self.env["res.city"].search([("ibge_code", "=", "3132404")], limit=1)

    def test_validacao_lista_os_campos_faltando(self):
        """Todos os campos obrigatórios ausentes saem numa mensagem só."""
        self.acidente.write(
            {
                "dsc_lograd": False,
                "date_atendimento": False,
                "hora_atendimento": False,
                "dur_trat": 0,
                "natureza_lesao_id": False,
                "cid_id": False,
                "nm_emit": False,
                "ide_oc_emit": False,
            }
        )
        evento = self.cat.action_gerar_s2210()
        with self.assertRaises(UserError) as erro:
            evento._validar_antes_do_envio()
        mensagem = str(erro.exception)
        for rotulo in (
            "logradouro e número do local do acidente",
            "data do atendimento",
            "hora do atendimento",
            "duração do tratamento",
            "natureza da lesão",
            "CID",
            "emitente do atestado",
            "órgão de classe e número do emitente",
        ):
            self.assertIn(rotulo, mensagem)
        self.assertNotIn("situação geradora", mensagem)

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_gerar_evento_valida_antes(self):
        evento = self.cat.action_gerar_s2210()
        self.acidente.nm_emit = False
        with self.assertRaisesRegex(UserError, "emitente do atestado"):
            evento.action_gerar_evento()
        self.assertFalse(evento.evento_id)
        self.acidente.nm_emit = "Dr. Plantonista"
        registro = evento.action_gerar_evento()
        self.assertEqual(registro.tipo, "S-2210")
        self.assertTrue(registro.id_evento)
        self.assertEqual(self.cat.esocial_evento_id, registro)

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_local_no_estabelecimento_completo(self):
        cidade = self._cidade()
        self.acidente.write(
            {
                "city_id": cidade.id,
                "state_id": cidade.state_id.id,
                "tp_insc_local": "1",
                "nr_insc_local": "02546716000146",
            }
        )
        evento = self.cat.action_gerar_s2210()
        dados = evento._to_esociallib_dict()
        self.assertEqual(dados["tp_local"], 1)
        self.assertEqual(dados["cep_local"], "37500000")
        self.assertEqual(dados["cod_munic_local"], "3132404")
        self.assertEqual(dados["uf_local"], "MG")
        self.assertEqual(dados["tp_insc_local"], 1)
        self.assertEqual(dados["nr_insc_local"], "02546716000146")
        root = self._xml(evento)
        ns = {"e": NS_2210}
        local = root.find(".//e:cat/e:localAcidente", ns)
        self.assertEqual(local.find("e:codMunic", ns).text, "3132404")
        self.assertEqual(local.find("e:uf", ns).text, "MG")
        self.assertEqual(local.find("e:cep", ns).text, "37500000")
        self.assertEqual(
            local.find("e:ideLocalAcid/e:nrInsc", ns).text, "02546716000146"
        )

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_local_no_exterior(self):
        """tpLocal 2: codPostal obrigatório; cep, codMunic e uf não se informam."""
        cidade = self._cidade()
        self.acidente.write(
            {
                "tp_local": "2",
                "cep_local": False,
                "city_id": cidade.id,
                "state_id": cidade.state_id.id,
                "country_id": self.env.ref("base.ar").id,
            }
        )
        evento = self.cat.action_gerar_s2210()
        with self.assertRaisesRegex(UserError, "código postal do local no exterior"):
            evento._validar_antes_do_envio()
        self.acidente.cep_local = "C1425"
        dados = evento._to_esociallib_dict()
        self.assertEqual(dados["tp_local"], 2)
        self.assertEqual(dados["cod_postal_local"], "C1425")
        self.assertEqual(dados["pais_local"], "063")
        for chave in ("cep_local", "cod_munic_local", "uf_local"):
            self.assertNotIn(chave, dados)
        ns = {"e": NS_2210}
        local = self._xml(evento).find(".//e:cat/e:localAcidente", ns)
        self.assertEqual(local.find("e:codPostal", ns).text, "C1425")
        self.assertEqual(local.find("e:pais", ns).text, "063")
        for tag in ("cep", "codMunic", "uf"):
            self.assertIsNone(local.find(f"e:{tag}", ns))

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_local_em_embarcacao_sem_endereco_postal(self):
        """Em embarcação o leiaute não exige CEP, município nem UF."""
        self.acidente.write({"tp_local": "6", "cep_local": False})
        evento = self.cat.action_gerar_s2210()
        dados = evento._to_esociallib_dict()
        self.assertEqual(dados["tp_local"], 6)
        for chave in ("cep_local", "cod_munic_local", "uf_local", "tp_insc_local"):
            self.assertNotIn(chave, dados)
        root = self._xml(evento)
        ns = {"e": NS_2210}
        local = root.find(".//e:cat/e:localAcidente", ns)
        self.assertEqual(local.find("e:tpLocal", ns).text, "6")
        for tag in ("cep", "codMunic", "uf", "ideLocalAcid"):
            self.assertIsNone(local.find(f"e:{tag}", ns))

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_houve_afastamento_sempre_informado(self):
        """cat/houveAfast é obrigatório a partir de 16/01/2023: vai S ou N."""
        evento = self.cat.action_gerar_s2210()
        ns = {"e": NS_2210}
        self.assertEqual(evento._to_esociallib_dict()["houve_afast"], "S")
        self.assertEqual(self._xml(evento).find(".//e:cat/e:houveAfast", ns).text, "S")
        self.acidente.write({"houve_afastamento": False, "ind_afast": "N"})
        self.assertEqual(evento._to_esociallib_dict()["houve_afast"], "N")
        self.assertEqual(self._xml(evento).find(".//e:cat/e:houveAfast", ns).text, "N")

    def test_ultimo_dia_trabalhado_obrigatorio_desde_16_01_2023(self):
        """cat/ultDiaTrab é obrigatório se dtAcid >= 2023-01-16."""
        evento = self.cat.action_gerar_s2210()
        self.acidente.ultimo_dia_trabalhado = False
        with self.assertRaisesRegex(UserError, "último dia trabalhado"):
            evento._validar_antes_do_envio()
        self.acidente.date_acidente = date(2023, 1, 16)
        with self.assertRaisesRegex(UserError, "último dia trabalhado"):
            evento._validar_antes_do_envio()
        self.acidente.date_acidente = date(2023, 1, 15)
        self.assertNotIn("ult_dia_trab", evento._to_esociallib_dict())

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_ultimo_dia_trabalhado(self):
        evento = self.cat.action_gerar_s2210()
        self.assertEqual(evento._to_esociallib_dict()["ult_dia_trab"], "2026-06-10")
        self.acidente.ultimo_dia_trabalhado = date(2026, 6, 9)
        self.assertEqual(evento._to_esociallib_dict()["ult_dia_trab"], "2026-06-09")
        root = self._xml(evento)
        self.assertEqual(
            root.find(".//e:cat/e:ultDiaTrab", {"e": NS_2210}).text, "2026-06-09"
        )

    def test_emitente_crm_ou_cro_exige_uf(self):
        """emitente/ufOC é obrigatório se ideOC = 1 (CRM) ou 2 (CRO)."""
        evento = self.cat.action_gerar_s2210()
        rotulo = "UF do órgão de classe do emitente"
        for ide_oc in ("1", "2"):
            self.acidente.write({"ide_oc_emit": ide_oc, "uf_oc_emit": False})
            with self.assertRaisesRegex(UserError, rotulo):
                evento._validar_antes_do_envio()
        self.acidente.uf_oc_emit = "sp"
        self.assertEqual(evento._to_esociallib_dict()["uf_oc"], "SP")

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_emitente_rms_dispensa_uf(self):
        """A UF do órgão de classe só é exigida para CRM e CRO."""
        self.acidente.write({"ide_oc_emit": "3", "uf_oc_emit": False})
        evento = self.cat.action_gerar_s2210()
        dados = evento._to_esociallib_dict()
        self.assertEqual(dados["ide_oc"], 3)
        self.assertEqual(dados["nr_oc"], "123456")
        self.assertNotIn("uf_oc", dados)
        ns = {"e": NS_2210}
        emitente = self._xml(evento).find(".//e:atestado/e:emitente", ns)
        self.assertEqual(emitente.find("e:ideOC", ns).text, "3")
        self.assertIsNone(emitente.find("e:ufOC", ns))

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_reabertura_leva_o_recibo_da_cat_de_origem(self):
        self.cat.action_emitir()
        self.assertNotIn("nr_rec_cat_orig", self.cat.s2210_id._to_esociallib_dict())
        self.cat.numero_recibo = "1.1.1234567890123456789"
        reabertura = self.acidente._criar_cat("2")
        evento = reabertura.action_gerar_s2210()
        dados = evento._to_esociallib_dict()
        self.assertEqual(dados["tp_cat"], 2)
        self.assertEqual(dados["nr_rec_cat_orig"], "1.1.1234567890123456789")
        root = self._xml(evento)
        self.assertEqual(
            root.find(".//e:cat/e:catOrigem/e:nrRecCatOrig", {"e": NS_2210}).text,
            "1.1.1234567890123456789",
        )

    def test_gerar_s2210_nao_duplica_e_abre_o_evento(self):
        self.cat.action_emitir()
        evento = self.cat.s2210_id
        self.assertEqual(self.cat.action_gerar_s2210(), evento)
        self.assertEqual(
            self.env["l10n_br.esocial.s2210"].search_count(
                [("cat_id", "=", self.cat.id)]
            ),
            1,
        )
        acao = self.cat.action_view_s2210()
        self.assertEqual(acao["res_model"], "l10n_br.esocial.s2210")
        self.assertEqual(acao["res_id"], evento.id)
