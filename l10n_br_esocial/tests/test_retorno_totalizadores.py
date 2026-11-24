# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import tagged

from ..models.retorno_totalizadores import parse_totalizadores
from .common import (
    RECIBO_S1210,
    RECIBO_S1299,
    ESocialCicloCommon,
    retorno_s5001,
    retorno_s5011,
)

NS_5002 = "http://www.esocial.gov.br/schema/evt/evtIrrfBenef/v_S_01_03_00"
NS_5011 = "http://www.esocial.gov.br/schema/evt/evtCS/v_S_01_03_00"

# S-5002 no leiaute S-1.3: detalhe por demonstrativo (dmDev/totApurMen) e
# consolidado do beneficiário (totInfoIR/consolidApurMen).
_TEMPLATE_S5002 = """<evento Id="IDBASE1210">
      <retornoEvento>
        <recibo><nrRecibo>{recibo}</nrRecibo></recibo>
        <tot>
          <eSocial xmlns="{ns}">
            <evtIrrfBenef Id="ID5002">
              <ideEvento>
                <nrRecArqBase>{recibo}</nrRecArqBase>
                <perApur>{per_apur}</perApur>
              </ideEvento>
              <ideEmpregador><tpInsc>1</tpInsc><nrInsc>02546716</nrInsc></ideEmpregador>
              <ideTrabalhador>
                <cpfBenef>{cpf}</cpfBenef>
                <dmDev>
                  <perRef>{per_apur}</perRef>
                  <ideDmDev>FOLHA-{per_apur}</ideDmDev>
                  <tpPgto>1</tpPgto>
                  <dtPgto>2024-04-05</dtPgto>
                  <codCateg>101</codCateg>
                  <infoIR><tpInfoIR>11</tpInfoIR><valor>3000.00</valor></infoIR>
                  <totApurMen>
                    <CRMen>056107</CRMen>
                    <vlrRendTrib>3000.00</vlrRendTrib>
                    <vlrPrevOficial>330.00</vlrPrevOficial>
                    <vlrCRMen>{irrf}</vlrCRMen>
                  </totApurMen>
                </dmDev>
                <totInfoIR>
                  <consolidApurMen>
                    <CRMen>056107</CRMen>
                    <vlrRendTrib>3000.00</vlrRendTrib>
                    <vlrPrevOficial>330.00</vlrPrevOficial>
                    <vlrCRMen>{irrf}</vlrCRMen>
                  </consolidApurMen>
                </totInfoIR>
              </ideTrabalhador>
            </evtIrrfBenef>
          </eSocial>
        </tot>
      </retornoEvento>
    </evento>"""

# S-5011 com código de receita por estabelecimento e base do 13º salário.
_TEMPLATE_S5011_ESTAB = """<evento Id="IDBASE1299">
      <retornoEvento>
        <tot>
          <eSocial xmlns="{ns}">
            <evtCS Id="ID5011">
              <ideEvento><indApuracao>1</indApuracao><perApur>2024-03</perApur></ideEvento>
              <ideEmpregador><tpInsc>1</tpInsc><nrInsc>02546716</nrInsc></ideEmpregador>
              <infoCS>
                <nrRecArqBase>{recibo}</nrRecArqBase>
                <indExistInfo>1</indExistInfo>
                <ideEstab>
                  <tpInsc>1</tpInsc>
                  <nrInsc>02546716000146</nrInsc>
                  <ideLotacao>
                    <codLotacao>LOT001</codLotacao>
                    <fpas>515</fpas>
                    <codTercs>0079</codTercs>
                    <basesRemun>
                      <indIncid>1</indIncid>
                      <codCateg>101</codCateg>
                      <basesCp><vrBcCp00>3000.00</vrBcCp00></basesCp>
                      <basesCp13><vrBcCp00>1500.00</vrBcCp00></basesCp13>
                    </basesRemun>
                  </ideLotacao>
                  <infoCREstab><tpCR>108201</tpCR><vrCR>330.00</vrCR></infoCREstab>
                </ideEstab>
              </infoCS>
            </evtCS>
          </eSocial>
        </tot>
      </retornoEvento>
    </evento>"""


def retorno_s5002(cpf, per_apur="2024-03", irrf=85.2):
    return _TEMPLATE_S5002.format(
        ns=NS_5002,
        cpf=cpf,
        per_apur=per_apur,
        irrf=f"{irrf:.2f}",
        recibo=RECIBO_S1210,
    )


@tagged("post_install", "-at_install")
class TestRetornoTotalizadores(ESocialCicloCommon):
    """Leitura dos totalizadores e conferência a partir deles."""

    def _totalizadores(self, tipo, retorno_xml, recibo=RECIBO_S1210):
        evento = self._criar_evento(tipo, state="sent", per_apur="2024-03")
        evento.registrar_aceite(nr_recibo=recibo, retorno_xml=retorno_xml)
        return evento

    def _linha(self, totalizador, grupo, descricao):
        return totalizador.linha_ids.filtered(
            lambda linha: linha.grupo == grupo and linha.descricao == descricao
        )

    # -- Leitura -------------------------------------------------------------

    def test_s5002_le_o_consolidado_do_beneficiario(self):
        evento = self._totalizadores("S-1210", retorno_s5002(self.cpf_employee))
        totalizador = evento.totalizador_ids
        self.assertEqual(totalizador.tipo, "S-5002")
        self.assertEqual(totalizador.per_apur, "2024-03")
        self.assertEqual(totalizador.nr_rec_arq_base, RECIBO_S1210)
        self.assertEqual(set(totalizador.linha_ids.mapped("grupo")), {"cr_men"})
        self.assertEqual(set(totalizador.linha_ids.mapped("codigo")), {"056107"})
        irrf = self._linha(totalizador, "cr_men", "vlrCRMen")
        self.assertEqual(len(irrf), 1)
        self.assertAlmostEqual(irrf.valor, 85.2, places=2)
        self.assertFalse(irrf.per_ref)
        rend = self._linha(totalizador, "cr_men", "vlrRendTrib")
        self.assertAlmostEqual(rend.valor, 3000.0, places=2)

    def test_s5011_por_estabelecimento_e_13(self):
        evento = self._totalizadores(
            "S-1299",
            _TEMPLATE_S5011_ESTAB.format(ns=NS_5011, recibo=RECIBO_S1299),
            recibo=RECIBO_S1299,
        )
        totalizador = evento.totalizador_ids
        cr_estab = self._linha(totalizador, "cr_estab", "vrCR")
        self.assertEqual(cr_estab.codigo, "108201")
        self.assertAlmostEqual(cr_estab.valor, 330.0, places=2)
        self.assertEqual(cr_estab.tp_insc, "1")
        self.assertEqual(cr_estab.nr_insc, "02546716000146")
        base13 = self._linha(totalizador, "base_cp13", "vrBcCp00")
        self.assertAlmostEqual(base13.valor, 1500.0, places=2)
        self.assertEqual(base13.cod_categ, "101")
        self.assertEqual(base13.cod_lotacao, "LOT001")
        base = self._linha(totalizador, "base_cp", "vrBcCp00")
        self.assertAlmostEqual(base.valor, 3000.0, places=2)

    def test_valor_ausente_vira_zero(self):
        """Base sem o campo valor não derruba a leitura do totalizador."""
        retorno = retorno_s5001(self.cpf_employee).replace("<valor>3000.00</valor>", "")
        (totalizador,) = parse_totalizadores(retorno)
        base = [linha for linha in totalizador.linhas if linha.grupo == "base_cs"]
        self.assertEqual(len(base), 1)
        self.assertEqual(base[0].valor, 0.0)
        self.assertEqual(base[0].codigo, "11")

    def test_retorno_vazio_nao_cria_totalizador(self):
        evento = self._criar_evento("S-1200", state="sent", per_apur="2024-03")
        totalizador = self.env["l10n_br.esocial.totalizador"]
        self.assertEqual(parse_totalizadores(""), [])
        self.assertFalse(totalizador.criar_do_retorno(evento, False))
        self.assertFalse(evento.totalizador_ids)

    def test_nome_e_contadores(self):
        evento = self._totalizadores("S-1200", retorno_s5001(self.cpf_employee))
        totalizador = evento.totalizador_ids
        self.assertEqual(evento.totalizador_count, 1)
        self.assertEqual(totalizador.name, f"S-5001 2024-03 {self.cpf_employee}")
        self.assertEqual(totalizador.linha_count, len(totalizador.linha_ids))
        self.assertEqual(totalizador.linha_count, 5)
        consolidado = self._totalizadores("S-1299", retorno_s5011()).totalizador_ids
        self.assertEqual(consolidado.name, "S-5011 2024-03")

    # -- Conferência ---------------------------------------------------------

    def test_conferencia_usa_s5002_sem_s5012(self):
        """Sem S-5012, o IRRF vem do consolidado do S-5002."""
        self._criar_payslip()
        self._totalizadores("S-1210", retorno_s5002(self.cpf_employee))
        conferencia = self.env["l10n_br.esocial.conferencia"].obter_ou_criar(
            self.company, "2024-03"
        )
        conferencia.action_apurar()
        irrf = conferencia.linha_ids.filtered(lambda linha: linha.indicador == "irrf")
        self.assertEqual(irrf.fonte_totalizador, "S-5002 consolidApurMen/vlrCRMen")
        self.assertAlmostEqual(irrf.valor_totalizador, 85.2, places=2)
        self.assertAlmostEqual(irrf.valor_folha, 85.2, places=2)
        self.assertFalse(irrf.divergente)

    def test_conferencia_anual_busca_holerites_do_ano(self):
        payslip = self._criar_payslip()
        conferencia = self.env["l10n_br.esocial.conferencia"].obter_ou_criar(
            self.company, "2024", ind_apuracao="2"
        )
        self.assertEqual(conferencia.payslip_ids, payslip)
        self.assertEqual(conferencia.payslip_sem_evento_ids, payslip)
        outro_ano = self.env["l10n_br.esocial.conferencia"].obter_ou_criar(
            self.company, "2023", ind_apuracao="2"
        )
        self.assertFalse(outro_ano.payslip_ids)

    def test_conferencia_nova_sem_competencia(self):
        """Formulário novo, antes de informar a competência."""
        conferencia = self.env["l10n_br.esocial.conferencia"].new(
            {"company_id": self.company.id}
        )
        self.assertEqual(conferencia.state, "draft")
        self.assertFalse(conferencia.totalizador_ids)
        self.assertFalse(conferencia.payslip_ids)
        with self.assertRaises(UserError) as erro:
            conferencia.action_apurar()
        self.assertIn("Informe o período de apuração", str(erro.exception))

    def test_conferencia_nao_apurada_fica_em_rascunho(self):
        conferencia = self.env["l10n_br.esocial.conferencia"].obter_ou_criar(
            self.company, "2024-03"
        )
        self.assertEqual(conferencia.state, "draft")
        self.assertEqual(conferencia.divergencia_count, 0)

    def test_ver_holerites_sem_evento(self):
        payslip = self._criar_payslip()
        conferencia = self.env["l10n_br.esocial.conferencia"].obter_ou_criar(
            self.company, "2024-03"
        )
        acao = conferencia.action_ver_holerites_sem_evento()
        self.assertEqual(acao["res_model"], "hr.payslip")
        self.assertEqual(acao["domain"], [("id", "in", payslip.ids)])
