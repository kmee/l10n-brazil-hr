# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import unittest

from lxml import etree

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import HAS_ESOCIALLIB, EsocialSstCommon

NS_2240 = "http://www.esocial.gov.br/schema/evt/evtExpRisco/v_S_01_03_00"


@tagged("post_install", "-at_install")
class TestS2240(EsocialSstCommon):
    """RS-16 e RS-17: S-2240 com epiEpc, validações e geração em massa."""

    def _cria_s2240(self):
        self._entrega_epi()
        return self.env["l10n_br.esocial.s2240"].gerar_para_contrato(
            self.contract, data=self.hoje
        )

    # ── Montagem ────────────────────────────────────────────────────────────

    def test_gerar_para_contrato(self):
        evento = self._cria_s2240()
        self.assertEqual(evento.employee_id, self.employee)
        self.assertEqual(evento.ambiente_id, self.ambiente)
        self.assertIn(self.risco, evento.risco_ids)
        self.assertIn(self.responsavel, evento.responsavel_ids)

    def test_sem_ambiente_nao_gera(self):
        self.contract.l10n_br_sst_ambiente_id = False
        evento = self.env["l10n_br.esocial.s2240"].gerar_para_contrato(
            self.contract, data=self.hoje
        )
        self.assertFalse(evento)

    def test_dsc_ativ_des_vem_do_ambiente(self):
        evento = self._cria_s2240()
        self.assertEqual(evento.dsc_ativ_des, "Operação de envasadora automática.")

    def test_ag_noc_com_epi_entregue(self):
        evento = self._cria_s2240()
        ag_noc = evento._to_ag_noc(self.risco)
        self.assertEqual(ag_noc["cod_ag_noc"], "02.01.001")
        self.assertEqual(ag_noc["utiliz_epi"], 2)
        self.assertEqual(ag_noc["efic_epi"], "S")
        self.assertEqual(ag_noc["epi"], [{"doc_aval": "31000"}])
        self.assertEqual(ag_noc["higienizacao"], "S")

    def test_ag_noc_ausencia_de_risco(self):
        risco = self.env["l10n_br.sst.risco"].create(
            {
                "ambiente_id": self.ambiente.id,
                "agente_nocivo_id": self.agente_ausencia.id,
                "laudo_id": self.laudo.id,
                "date_from": self.hoje,
            }
        )
        evento = self._cria_s2240()
        ag_noc = evento._to_ag_noc(risco)
        self.assertEqual(ag_noc["utiliz_epc"], 0)
        self.assertEqual(ag_noc["utiliz_epi"], 0)
        self.assertNotIn("epi", ag_noc)

    def test_ag_noc_qualitativo_por_decisao_judicial(self):
        """05.01.001 leva descrição e processo, sem medição e sem EPI."""
        risco = self.env["l10n_br.sst.risco"].create(
            {
                "ambiente_id": self.ambiente.id,
                "laudo_id": self.laudo.id,
                "agente_nocivo_id": self.env.ref(
                    "l10n_br_esocial.agente_noc_05_01_001"
                ).id,
                "descricao": "Agente incluído por decisão judicial",
                "tp_aval": "2",
                "nr_proc_jud": "00012342620268130001",
                "utiliz_epc": "2",
                "efic_epc": "S",
                "utiliz_epi": "1",
                "date_from": "2026-01-01",
            }
        )
        evento = self._cria_s2240()
        self.assertIn(risco, evento.risco_ids)
        ag_noc = evento._to_ag_noc(risco)
        self.assertEqual(ag_noc["cod_ag_noc"], "05.01.001")
        self.assertEqual(ag_noc["dsc_ag_noc"], "Agente incluído por decisão judicial")
        self.assertEqual(ag_noc["tp_aval"], 2)
        self.assertEqual(ag_noc["nr_proc_jud"], "00012342620268130001")
        self.assertEqual(ag_noc["utiliz_epc"], 2)
        self.assertEqual(ag_noc["efic_epc"], "S")
        self.assertEqual(ag_noc["utiliz_epi"], 1)
        for chave in ("int_conc", "lim_tol", "un_med", "tec_medicao", "efic_epi"):
            self.assertNotIn(chave, ag_noc)
        self.assertNotIn("epi", ag_noc)
        # EPI não utilizado dispensa eficácia e entrega na validação.
        self.assertTrue(evento.action_validar())

    # ── Validações antes do envio (RS-17) ───────────────────────────────────

    def test_valida_sem_epi_entregue(self):
        """Declarar uso de EPI sem entrega válida é erro antes do envio."""
        evento = self.env["l10n_br.esocial.s2240"].gerar_para_contrato(
            self.contract, data=self.hoje
        )
        with self.assertRaises(UserError):
            evento.action_validar()

    def test_valida_sem_responsavel(self):
        evento = self._cria_s2240()
        evento.responsavel_ids = [(5, 0, 0)]
        with self.assertRaises(UserError):
            evento.action_validar()

    def test_valida_sem_risco(self):
        evento = self._cria_s2240()
        evento.risco_ids = [(5, 0, 0)]
        with self.assertRaises(UserError):
            evento.action_validar()

    def test_valida_ausencia_com_outros_riscos(self):
        evento = self._cria_s2240()
        risco_ausencia = self.env["l10n_br.sst.risco"].create(
            {
                "ambiente_id": self.ambiente.id,
                "agente_nocivo_id": self.agente_ausencia.id,
                "date_from": self.hoje,
            }
        )
        evento.risco_ids = [(4, risco_ausencia.id)]
        with self.assertRaises(UserError):
            evento.action_validar()

    def test_valida_epc_sem_eficacia(self):
        evento = self._cria_s2240()
        self.risco.write({"utiliz_epc": "2", "efic_epc": False})
        with self.assertRaises(UserError):
            evento.action_validar()

    def test_valida_epi_sem_eficacia(self):
        evento = self._cria_s2240()
        self.risco.efic_epi = False
        with self.assertRaises(UserError):
            evento.action_validar()

    def test_valida_so_ausencia_de_risco(self):
        """Ausência sozinha no evento é válida, sem EPC, EPI nem entrega."""
        risco_ausencia = self.env["l10n_br.sst.risco"].create(
            {
                "ambiente_id": self.ambiente.id,
                "agente_nocivo_id": self.agente_ausencia.id,
                "laudo_id": self.laudo.id,
                "date_from": self.hoje,
            }
        )
        evento = self.env["l10n_br.esocial.s2240"].gerar_para_contrato(
            self.contract, data=self.hoje
        )
        evento.risco_ids = [(6, 0, risco_ausencia.ids)]
        self.assertTrue(evento.action_validar())

    def test_valida_ok(self):
        evento = self._cria_s2240()
        self.assertTrue(evento.action_validar())

    def test_responsavel_vem_do_laudo_informado(self):
        """Risco sem laudo: o responsável sai do laudo que dispara a geração."""
        self.risco.laudo_id = False
        sem_laudo = self.env["l10n_br.esocial.s2240"].gerar_para_contrato(
            self.contract, data=self.hoje
        )
        self.assertFalse(sem_laudo.responsavel_ids)
        evento = self.env["l10n_br.esocial.s2240"].gerar_para_contrato(
            self.contract, data=self.hoje, laudo=self.laudo
        )
        self.assertEqual(evento.laudo_id, self.laudo)
        self.assertEqual(evento.responsavel_ids, self.responsavel)

    # ── Geração em massa ────────────────────────────────────────────────────

    def test_gerar_em_massa_pelo_laudo(self):
        self._entrega_epi()
        acao = self.laudo.action_gerar_s2240()
        eventos = self.env["l10n_br.esocial.s2240"].search(acao["domain"])
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos.employee_id, self.employee)

    def test_gerar_em_massa_nao_duplica(self):
        self._entrega_epi()
        self.laudo.action_gerar_s2240()
        acao = self.laudo.action_gerar_s2240()
        self.assertFalse(self.env["l10n_br.esocial.s2240"].search(acao["domain"]))

    def test_laudo_conta_e_abre_os_eventos(self):
        self._entrega_epi()
        self.assertEqual(self.laudo.s2240_count, 0)
        self.laudo.action_gerar_s2240()
        self.assertEqual(self.laudo.s2240_count, 1)
        acao = self.laudo.action_view_s2240()
        self.assertEqual(
            self.env["l10n_br.esocial.s2240"].search(acao["domain"]),
            self.laudo.s2240_ids,
        )
        self.assertEqual(self.laudo.s2240_ids.employee_id, self.employee)

    def test_laudo_sem_contrato_nos_ambientes(self):
        ambiente = self.env["l10n_br.sst.ambiente"].create(
            {
                "name": "Almoxarifado",
                "dsc_setor": "ALMOXARIFADO",
                "local_amb": "1",
                "tp_insc": "1",
                "nr_insc": "02546716000146",
            }
        )
        laudo = self.env["l10n_br.sst.laudo"].create(
            {
                "name": "PGR Almoxarifado",
                "date_from": self.hoje,
                "responsavel_id": self.responsavel.id,
            }
        )
        self.env["l10n_br.sst.risco"].create(
            {
                "ambiente_id": ambiente.id,
                "laudo_id": laudo.id,
                "agente_nocivo_id": self.agente_ausencia.id,
                "date_from": self.hoje,
            }
        )
        laudo.action_vigente()
        with self.assertRaisesRegex(UserError, "nenhum contrato aberto"):
            laudo.action_gerar_s2240()

    def test_laudo_em_rascunho_nao_gera(self):
        laudo = self.env["l10n_br.sst.laudo"].create(
            {"name": "PGR rascunho", "date_from": self.hoje}
        )
        with self.assertRaises(UserError):
            laudo.action_gerar_s2240()

    # ── XML ─────────────────────────────────────────────────────────────────

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_xml_do_evento(self):
        evento = self._cria_s2240()
        xml = evento._gerar_xml()
        root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
        ns = {"e": NS_2240}
        self.assertEqual(root.find(".//e:agNoc/e:codAgNoc", ns).text, "02.01.001")
        self.assertEqual(root.find(".//e:epcEpi/e:epi/e:docAval", ns).text, "31000")
        self.assertEqual(root.find(".//e:infoAmb/e:dscSetor", ns).text, "PRODUCAO")
        self.assertEqual(root.find(".//e:respReg/e:cpfResp", ns).text, "07616692941")
        self.assertEqual(root.find(".//e:ideVinculo/e:cpfTrab", ns).text, "07616692990")

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_evento_preenche_id_evento(self):
        """O ciclo do PR do S-1005 vale para o SST: sem Id não casa o retorno."""
        evento = self._cria_s2240()
        registro = evento.action_gerar_evento()
        self.assertTrue(registro.id_evento)
        self.assertEqual(registro.tipo, "S-2240")

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_fim_da_condicao_e_observacao(self):
        evento = self._cria_s2240()
        dados = evento._to_esociallib_dict()
        self.assertNotIn("dt_fim_condicao", dados)
        self.assertNotIn("obs_compl", dados)
        evento.write(
            {
                "dt_fim_condicao": self.hoje,
                "obs_compl": "Medição refeita após troca do enclausuramento.",
            }
        )
        dados = evento._to_esociallib_dict()
        self.assertEqual(dados["dt_fim_condicao"], str(self.hoje))
        self.assertEqual(
            dados["obs_compl"], "Medição refeita após troca do enclausuramento."
        )
        xml = evento._gerar_xml()
        root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
        ns = {"e": NS_2240}
        self.assertEqual(
            root.find(".//e:infoExpRisco/e:dtFimCondicao", ns).text, str(self.hoje)
        )
        self.assertEqual(
            root.find(".//e:obsCompl", ns).text,
            "Medição refeita após troca do enclausuramento.",
        )
