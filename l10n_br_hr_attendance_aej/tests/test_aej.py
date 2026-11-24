# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Testes do AEJ e do espelho de ponto (RP-20 a RP-23)."""

import base64
import sys
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from ..models import aej_layout
from ..models.l10n_br_hr_apuracao_periodo import L10nBrHrApuracaoPeriodo

_LOGGER_PERIODO = (
    "odoo.addons.l10n_br_hr_attendance_aej.models.l10n_br_hr_apuracao_periodo"
)


@tagged("post_install", "-at_install")
class TestAej(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.vat = "12.345.678/0001-95"
        # Com o l10n_br_fiscal_certificate instalado a empresa de demonstração
        # pode trazer um certificado de teste que não abre; a suíte parte de
        # "sem certificado" e cada teste de assinatura injeta o seu.
        patcher = patch.object(
            type(cls.env["l10n_br.hr.apuracao.periodo"]),
            "_certificado_ptrp",
            return_value=None,
        )
        patcher.start()
        cls.addClassCleanup(patcher.stop)
        cls.rep = cls.env["l10n_br.hr.rep"].create(
            {
                "name": "REP do AEJ",
                "tipo": "rep_c",
                "numero_fabricacao": "33333333333333333",
                "cnpj_cpf": "12345678000195",
                "atestado_date_start": "2020-01-01",
                "atestado_date_end": "2099-12-31",
            }
        )
        cls.calendario = cls.env["resource.calendar"].create(
            {
                "name": "Jornada AEJ",
                "tz": "America/Sao_Paulo",
                "hours_per_day": 8.0,
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": f"{dia} manhã",
                            "dayofweek": dia,
                            "hour_from": 8.0,
                            "hour_to": 12.0,
                        },
                    )
                    for dia in ("0", "1", "2", "3", "4")
                ]
                + [
                    (
                        0,
                        0,
                        {
                            "name": f"{dia} tarde",
                            "dayofweek": dia,
                            "hour_from": 13.0,
                            "hour_to": 17.0,
                        },
                    )
                    for dia in ("0", "1", "2", "3", "4")
                ],
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Beatriz Jornada",
                "tz": "America/Sao_Paulo",
                "resource_calendar_id": cls.calendario.id,
                "vat": "434.612.928-50",
            }
        )
        cls.contract = cls.env["hr.contract"].create(
            {
                "name": "Contrato Beatriz",
                "employee_id": cls.employee.id,
                "wage": 3000.0,
                "date_start": date(2026, 1, 1),
                "state": "open",
                "resource_calendar_id": cls.calendario.id,
                "company_id": cls.company.id,
            }
        )
        cls.nsr = 0

    @classmethod
    def _marcar(cls, dia, *horas_locais):
        vals = []
        for hora, minuto in horas_locais:
            cls.nsr += 1
            vals.append(
                {
                    "nsr": cls.nsr,
                    "rep_id": cls.rep.id,
                    "company_id": cls.company.id,
                    "employee_id": cls.employee.id,
                    "datetime_marcacao": datetime(2026, 3, dia, hora, minuto)
                    + timedelta(hours=3),
                    "origem": "rep_c",
                }
            )
        return cls.env["l10n_br.hr.marcacao"]._criar_marcacoes(vals)

    def _periodo(self, fechar=True, date_from=None, date_to=None):
        periodo = self.env["l10n_br.hr.apuracao.periodo"].create(
            {
                "name": "Março/2026 AEJ",
                "date_from": date_from or date(2026, 3, 2),
                "date_to": date_to or date(2026, 3, 3),
                "company_id": self.company.id,
                "employee_ids": [(6, 0, self.employee.ids)],
            }
        )
        periodo.action_apurar()
        if fechar:
            periodo.with_context(l10n_br_forcar_fechamento=True).action_fechar()
        return periodo

    def _linhas(self, conteudo):
        return [
            linha
            for linha in conteudo.split(aej_layout.TERMINADOR_LINHA)
            if linha.strip()
        ]

    def _por_tipo(self, conteudo, tipo):
        return [
            linha for linha in self._linhas(conteudo) if linha.startswith(tipo + "|")
        ]

    # ------------------------------------------------------------------

    def test_aej_so_de_competencia_fechada(self):
        """Arquivo entregue à fiscalização não pode mudar depois de emitido."""
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._periodo(fechar=False)
        with self.assertRaises(UserError):
            periodo.gerar_aej()

    def test_estrutura_do_arquivo(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._periodo()
        nome, conteudo = periodo.gerar_aej()
        linhas = self._linhas(conteudo)
        self.assertTrue(nome.startswith("AEJ12345678000195"))
        self.assertTrue(linhas[0].startswith("01|"))
        self.assertTrue(linhas[-1].startswith("99|"))
        self.assertTrue(conteudo.endswith(aej_layout.TERMINADOR_LINHA))
        # Cada linha tem exatamente os campos do seu tipo: campo opcional
        # vazio continua ocupando a sua posição entre pipes, senão o leitor do
        # fisco desloca todos os campos seguintes.
        for linha in linhas:
            tipo = linha.split("|")[0]
            self.assertEqual(
                len(linha.split("|")),
                len(aej_layout.CAMPOS[tipo]),
                f"Registro tipo {tipo} com número de campos diferente do leiaute",
            )

    def test_cabecalho_traz_periodo_e_versao(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._periodo()
        _nome, conteudo = periodo.gerar_aej()
        campos = self._por_tipo(conteudo, "01")[0].split("|")
        self.assertEqual(campos[1], "1")
        self.assertEqual(campos[2], "12345678000195")
        self.assertEqual(campos[6], "2026-03-02")
        self.assertEqual(campos[7], "2026-03-03")
        self.assertEqual(campos[9], aej_layout.VERSAO_LEIAUTE)

    def test_registro_02_identifica_o_rep(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._periodo()
        _nome, conteudo = periodo.gerar_aej()
        campos = self._por_tipo(conteudo, "02")[0].split("|")
        self.assertEqual(campos[2], "1")  # REP-C
        self.assertEqual(campos[3], "33333333333333333")

    def test_registro_03_traz_cpf_e_nome(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._periodo()
        _nome, conteudo = periodo.gerar_aej()
        campos = self._por_tipo(conteudo, "03")[0].split("|")
        self.assertEqual(campos[2], "43461292850")
        self.assertEqual(campos[3], "Beatriz Jornada")

    def test_registro_04_tem_duracao_em_minutos(self):
        """Anexo VI: durJornada é em minutos, não em horas."""
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._periodo()
        _nome, conteudo = periodo.gerar_aej()
        campos = self._por_tipo(conteudo, "04")[0].split("|")
        self.assertEqual(campos[2], "480")
        self.assertEqual(campos[3], "0800")
        self.assertEqual(campos[4], "1200")
        self.assertEqual(campos[5], "1300")
        self.assertEqual(campos[6], "1700")

    def test_registro_05_pareia_entradas_e_saidas(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._periodo()
        _nome, conteudo = periodo.gerar_aej()
        marcacoes = self._por_tipo(conteudo, "05")
        self.assertEqual(len(marcacoes), 4)
        tipos = [linha.split("|")[4] for linha in marcacoes]
        self.assertEqual(tipos, ["E", "S", "E", "S"])
        sequencias = [linha.split("|")[5] for linha in marcacoes]
        self.assertEqual(sequencias, ["001", "001", "002", "002"])

    def test_primeira_entrada_carrega_o_horario_contratual(self):
        """Campo obrigatório quando tpMarc = E e seqEntSaida = 1."""
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._periodo()
        _nome, conteudo = periodo.gerar_aej()
        primeira = self._por_tipo(conteudo, "05")[0].split("|")
        self.assertTrue(primeira[7])
        segunda = self._por_tipo(conteudo, "05")[1].split("|")
        self.assertFalse(segunda[7])

    def test_data_hora_tem_fuso_obrigatorio(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._periodo()
        _nome, conteudo = periodo.gerar_aej()
        marcacao = self._por_tipo(conteudo, "05")[0].split("|")[2]
        self.assertEqual(marcacao, "2026-03-02T08:00:00-0300")

    def test_marcacao_desconsiderada_entra_com_motivo(self):
        """O tratamento tem que ser visível: nada some do arquivo."""
        marcacoes = self._marcar(2, (8, 0), (8, 1), (12, 0), (13, 0), (17, 0))
        duplicada = marcacoes.filtered(
            lambda m: m.datetime_marcacao == datetime(2026, 3, 2, 11, 1)
        )
        duplicada.action_desconsiderar("Batida em duplicidade no relógio")
        periodo = self._periodo()
        _nome, conteudo = periodo.gerar_aej()
        descartadas = [
            linha
            for linha in self._por_tipo(conteudo, "05")
            if linha.split("|")[4] == "D"
        ]
        self.assertEqual(len(descartadas), 1)
        self.assertIn("duplicidade", descartadas[0])

    def test_falta_injustificada_vira_registro_07(self):
        periodo = self._periodo(date_from=date(2026, 3, 2), date_to=date(2026, 3, 2))
        _nome, conteudo = periodo.gerar_aej()
        ausencias = self._por_tipo(conteudo, "07")
        self.assertEqual(len(ausencias), 1)
        campos = ausencias[0].split("|")
        self.assertEqual(campos[2], aej_layout.AUSENCIA_FALTA)
        self.assertEqual(campos[3], "2026-03-02")

    def test_domingo_vira_dsr_no_registro_07(self):
        periodo = self._periodo(date_from=date(2026, 3, 1), date_to=date(2026, 3, 1))
        _nome, conteudo = periodo.gerar_aej()
        campos = self._por_tipo(conteudo, "07")[0].split("|")
        self.assertEqual(campos[2], aej_layout.AUSENCIA_DSR)

    def test_banco_de_horas_no_registro_07(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._periodo(fechar=False)
        dia = periodo.dia_ids.filtered(lambda d: d.date == date(2026, 3, 2))
        dia.banco_horas_delta = 1.5
        periodo.with_context(l10n_br_forcar_fechamento=True).action_fechar()
        _nome, conteudo = periodo.gerar_aej()
        movimentos = [
            linha
            for linha in self._por_tipo(conteudo, "07")
            if linha.split("|")[2] == aej_layout.AUSENCIA_BANCO_HORAS
        ]
        self.assertEqual(len(movimentos), 1)
        campos = movimentos[0].split("|")
        self.assertEqual(campos[4], "90")
        self.assertEqual(campos[5], aej_layout.BH_INCLUSAO)

    def test_registro_08_identifica_o_ptrp(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._periodo()
        _nome, conteudo = periodo.gerar_aej()
        campos = self._por_tipo(conteudo, "08")[0].split("|")
        self.assertEqual(campos[1], "Odoo PTRP")
        self.assertEqual(campos[2], "16.0")

    def test_trailer_conta_os_registros(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._periodo()
        _nome, conteudo = periodo.gerar_aej()
        campos = self._por_tipo(conteudo, "99")[0].split("|")
        self.assertEqual(campos[1], "1")  # cabeçalho
        self.assertEqual(campos[2], str(len(self._por_tipo(conteudo, "02"))))
        self.assertEqual(campos[3], str(len(self._por_tipo(conteudo, "03"))))
        self.assertEqual(campos[5], str(len(self._por_tipo(conteudo, "05"))))
        self.assertEqual(campos[8], "1")  # PTRP

    def test_geracao_anexa_o_arquivo(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._periodo()
        periodo.action_gerar_aej()
        self.assertTrue(periodo.aej_file)
        self.assertTrue(periodo.aej_date)
        conteudo = base64.b64decode(periodo.aej_file).decode(aej_layout.ENCODING_AEJ)
        self.assertTrue(conteudo.startswith("01|"))

    def test_sem_certificado_gera_sem_assinatura_e_avisa(self):
        """O RH não pode ficar sem arquivo por falta de certificado."""
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._periodo()
        periodo.action_gerar_aej()
        self.assertTrue(periodo.aej_file)
        self.assertFalse(periodo.aej_p7s)
        mensagens = periodo.message_ids.mapped("body")
        self.assertTrue(any("SEM assinatura" in corpo for corpo in mensagens))

    @mute_logger(
        "odoo.addons.l10n_br_hr_attendance_aej.models.l10n_br_hr_apuracao_periodo"
    )
    def test_certificado_invalido_gera_sem_assinatura_e_avisa(self):
        """Certificado que não abre não pode impedir a geração do arquivo."""
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._periodo()
        falso = SimpleNamespace(file=base64.b64encode(b"nao e pkcs12"), password="x")
        with patch.object(
            type(periodo), "_certificado_ptrp", return_value=falso, create=True
        ):
            periodo.action_gerar_aej()
        self.assertTrue(periodo.aej_file)
        self.assertFalse(periodo.aej_p7s)
        mensagens = periodo.message_ids.mapped("body")
        self.assertTrue(any("Falha ao assinar" in corpo for corpo in mensagens))

    def test_espelho_de_ponto_renderiza(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._periodo()
        html = self.env["ir.actions.report"]._render_qweb_html(
            "l10n_br_hr_attendance_aej.report_espelho_ponto", periodo.ids
        )[0]
        texto = html.decode() if isinstance(html, bytes) else html
        self.assertIn("Espelho de Ponto", texto)
        self.assertIn("Beatriz Jornada", texto)
        self.assertIn("434.612.928-50", texto)

    def test_arquivo_em_iso_8859_1(self):
        """Item 2 do Anexo VI: ASCII da norma ISO 8859-1."""
        self.company.name = "Açúcar e Cia Ltda"
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._periodo()
        _nome, conteudo = periodo.gerar_aej()
        bruto = conteudo.encode(aej_layout.ENCODING_AEJ)
        self.assertIn("Açúcar", bruto.decode(aej_layout.ENCODING_AEJ))

    def test_data_hora_vazia_fica_em_branco(self):
        self.assertEqual(aej_layout.formata_datetime(None), "")
        self.assertEqual(aej_layout.formata_datetime(False, -3), "")

    def test_marcacao_sem_par_entra_como_desconsiderada(self):
        """Sem par não se afirma entrada nem saída, mas a batida não some."""
        self._marcar(2, (8, 0), (12, 0), (13, 0))
        periodo = self._periodo()
        _nome, conteudo = periodo.gerar_aej()
        marcacoes = [linha.split("|") for linha in self._por_tipo(conteudo, "05")]
        self.assertEqual([campos[4] for campos in marcacoes], ["E", "S", "D"])
        sem_par = marcacoes[-1]
        self.assertEqual(sem_par[2], "2026-03-02T13:00:00-0300")
        self.assertEqual(sem_par[5], "000")
        self.assertEqual(sem_par[7], "")
        self.assertEqual(sem_par[8], "Marcação sem par no dia")

    def test_folga_compensatoria_vira_registro_07(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._periodo(
            fechar=False, date_from=date(2026, 3, 2), date_to=date(2026, 3, 2)
        )
        periodo.dia_ids.ocorrencia_ids = [
            (
                4,
                self.env.ref(
                    "l10n_br_hr_attendance_apuracao.ocorrencia_folga_compensatoria"
                ).id,
            )
        ]
        periodo.with_context(l10n_br_forcar_fechamento=True).action_fechar()
        _nome, conteudo = periodo.gerar_aej()
        ausencias = [linha.split("|") for linha in self._por_tipo(conteudo, "07")]
        self.assertEqual(len(ausencias), 1)
        self.assertEqual(ausencias[0][2], aej_layout.AUSENCIA_FOLGA_FERIADO)
        self.assertEqual(ausencias[0][3], "2026-03-02")

    def test_assinatura_gravada_junto_do_arquivo(self):
        """O .p7s assina exatamente os bytes do AEJ anexado (arts. 86 a 88)."""
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._periodo()
        with patch.object(
            type(periodo), "_assinar_aej", return_value=b"assinatura cades"
        ) as assinar:
            periodo.action_gerar_aej()
        bruto = base64.b64decode(periodo.aej_file)
        assinar.assert_called_once_with(bruto)
        self.assertEqual(base64.b64decode(periodo.aej_p7s), b"assinatura cades")
        self.assertEqual(periodo.aej_p7s_filename, periodo.aej_filename + ".p7s")

    def test_empresa_sem_certificado_nao_assina(self):
        periodo = self._periodo()
        empresa = periodo.company_id
        if "certificate_ecnpj_id" in empresa._fields:
            empresa.write({"certificate_ecnpj_id": False, "certificate_ecpf_id": False})
        # Chama o método original: a suíte substitui o da classe registrada.
        self.assertIsNone(L10nBrHrApuracaoPeriodo._certificado_ptrp(periodo))

    def test_sem_biblioteca_de_assinatura_gera_sem_assinatura(self):
        periodo = self._periodo()
        falso = SimpleNamespace(file=base64.b64encode(b"pkcs12"), password="x")
        with (
            patch.object(type(periodo), "_certificado_ptrp", return_value=falso),
            patch.dict(sys.modules, {"erpbrasil.assinatura": None}),
            self.assertLogs(_LOGGER_PERIODO, "WARNING") as registro,
        ):
            self.assertIsNone(periodo._assinar_aej(b"conteudo"))
        self.assertIn("erpbrasil.assinatura indisponível", registro.output[0])

    def test_acao_do_espelho_de_ponto(self):
        periodo = self._periodo()
        acao = periodo.with_context(discard_logo_check=True).action_imprimir_espelho()
        self.assertEqual(acao["type"], "ir.actions.report")
        self.assertEqual(
            acao["report_name"], "l10n_br_hr_attendance_aej.report_espelho_ponto"
        )
        self.assertEqual(acao["context"]["active_ids"], periodo.ids)
