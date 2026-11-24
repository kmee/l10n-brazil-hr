# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Testes da verificação de integridade do PTRP."""

from datetime import date
from unittest.mock import patch

from odoo.modules.module import get_module_path
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..models import ptrp_escopo
from ..models.l10n_br_hr_ptrp_integridade import (
    PARAM_RESUMO_HOMOLOGADO,
    PARAM_VERSAO_ATESTADA,
)


@tagged("post_install", "-at_install")
class TestIntegridadePtrp(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.verificador = cls.env["l10n_br.hr.ptrp.integridade"]
        cls.parametro = cls.env["ir.config_parameter"].sudo()

    def test_resumo_e_estavel_entre_chamadas(self):
        """Sem alteração no código, o resumo tem que se repetir."""
        self.assertEqual(
            self.verificador.resumo_fonte(), self.verificador.resumo_fonte()
        )

    def test_resumo_tem_formato_sha256(self):
        resumo = self.verificador.resumo_fonte()
        self.assertEqual(len(resumo), 64)
        int(resumo, 16)

    def test_todo_o_escopo_atestado_e_dependencia(self):
        """Instalar a integridade instala o escopo inteiro, AFD incluído.

        Sem o AFD no ``depends``, o manifesto de uma base sem o módulo
        registrava a ausência e o resumo mudava conforme a composição da
        instalação, não conforme o código atestado.
        """
        self.assertEqual(self.verificador._modulos_do_escopo_ausentes(), [])

    def test_manifesto_cobre_o_nucleo_declarado(self):
        manifesto = dict(self.verificador._manifesto_fonte())
        for arquivo in (
            "l10n_br_hr_attendance/models/l10n_br_hr_marcacao.py",
            "l10n_br_hr_attendance_afd/models/afd_crc.py",
            "l10n_br_hr_attendance_apuracao/models/regras_jornada.py",
            "l10n_br_hr_attendance_aej/models/aej_layout.py",
        ):
            self.assertIn(arquivo, manifesto)
            self.assertEqual(len(manifesto[arquivo]), 64)

    def test_escopo_nao_inclui_views_nem_testes(self):
        """Mudar tela ou teste não pode obrigar a reemitir o atestado."""
        caminhos = [caminho for caminho, _resumo in self.verificador._manifesto_fonte()]
        self.assertFalse([c for c in caminhos if "/views/" in c])
        self.assertFalse([c for c in caminhos if "/tests/" in c])
        self.assertFalse([c for c in caminhos if "/i18n/" in c])
        self.assertFalse([c for c in caminhos if c.endswith("README.rst")])

    def test_alteracao_no_nucleo_muda_o_resumo(self):
        """O resumo precisa reagir a uma linha diferente no escopo."""
        entradas = self.verificador._manifesto_fonte()
        original = ptrp_escopo.resumo_do_manifesto(entradas)
        adulterado = [(caminho, resumo) for caminho, resumo in entradas]
        adulterado[0] = (adulterado[0][0], "0" * 64)
        self.assertNotEqual(ptrp_escopo.resumo_do_manifesto(adulterado), original)

    def test_ordem_dos_arquivos_nao_altera_o_resumo(self):
        """O texto canônico é ordenado: a ordem de leitura não pode importar."""
        entradas = self.verificador._manifesto_fonte()
        self.assertEqual(
            ptrp_escopo.resumo_do_manifesto(entradas),
            ptrp_escopo.resumo_do_manifesto(list(reversed(entradas))),
        )

    def test_sem_homologado_a_conferencia_fica_indefinida(self):
        self.parametro.set_param(PARAM_RESUMO_HOMOLOGADO, "")
        estado = self.verificador.verificar()
        self.assertIsNone(estado["confere"])
        self.assertIn(
            "Não há resumo homologado", self.verificador.texto_do_diagnostico()
        )

    def test_homologado_igual_confere(self):
        self.parametro.set_param(
            PARAM_RESUMO_HOMOLOGADO, self.verificador.resumo_fonte()
        )
        self.parametro.set_param(PARAM_VERSAO_ATESTADA, "16.0.1")
        estado = self.verificador.verificar()
        self.assertTrue(estado["confere"])
        self.assertIn(
            "confere com o homologado", self.verificador.texto_do_diagnostico()
        )

    def test_homologado_diferente_acusa_divergencia(self):
        self.parametro.set_param(PARAM_RESUMO_HOMOLOGADO, "f" * 64)
        estado = self.verificador.verificar()
        self.assertFalse(estado["confere"])
        self.assertIn("DIVERGE do homologado", self.verificador.texto_do_diagnostico())

    def test_acao_de_servidor_sobre_modelo_atestado_e_detectada(self):
        """Código em banco altera o resultado sem tocar em arquivo nenhum."""
        modelo = self.env["ir.model"]._get("l10n_br.hr.apuracao.dia")
        self.env["ir.actions.server"].create(
            {
                "name": "Ajuste silencioso de apuração",
                "model_id": modelo.id,
                "state": "code",
                "code": "records.write({'horas_extras': 0})",
            }
        )
        divergencias = self.verificador._codigo_em_banco()
        self.assertTrue(
            any("Ajuste silencioso" in item for item in divergencias), divergencias
        )
        self.assertIn("Ação de servidor", self.verificador.texto_do_diagnostico())

    def test_modulo_do_escopo_ausente_aparece_no_manifesto(self):
        """Composição faz parte do que se atesta: ausência não pode sumir.

        Se um módulo do escopo não está instalado, o manifesto tem que dizer
        isso, senão duas instalações diferentes produziriam resumos diferentes
        sem explicação em lugar nenhum.
        """
        caminhos = [caminho for caminho, _r in self.verificador._manifesto_fonte()]
        for modulo in self.verificador._modulos_do_escopo_ausentes():
            self.assertIn(ptrp_escopo.marca_de_ausencia(modulo), caminhos)

    def test_todo_modulo_do_escopo_esta_representado(self):
        caminhos = [caminho for caminho, _r in self.verificador._manifesto_fonte()]
        for modulo in ptrp_escopo.NUCLEO_ATESTADO:
            self.assertTrue(
                any(caminho.startswith(modulo + "/") for caminho in caminhos),
                f"Módulo {modulo} não aparece no manifesto",
            )

    def test_modulos_do_ptrp_nao_contam_como_extensao(self):
        """Os próprios módulos da suíte não podem aparecer como intrusos."""
        self.assertFalse(self.verificador._extensoes_de_terceiros())

    def test_manifesto_impresso_permite_recalcular(self):
        texto = self.verificador.imprimir_manifesto()
        linhas = texto.strip().split("\n")
        self.assertTrue(linhas[-1].startswith("resumo="))
        entradas = [
            tuple(linha.rsplit(":", 1)) for linha in linhas[:-2] if ":" in linha
        ]
        self.assertEqual(
            ptrp_escopo.resumo_do_manifesto(entradas),
            linhas[-1].split("=", 1)[1],
        )

    def test_padrao_sem_arquivo_entra_com_resumo_vazio(self):
        """Arquivo declarado que sumiu do disco não pode sumir do manifesto."""
        caminho = get_module_path("l10n_br_hr_attendance_integridade")
        entradas = ptrp_escopo.manifesto_do_modulo(
            caminho,
            "l10n_br_hr_attendance_integridade",
            ("models/ptrp_escopo.py", "models/arquivo_removido.py"),
        )
        self.assertEqual(
            entradas[0],
            ("l10n_br_hr_attendance_integridade/models/arquivo_removido.py", ""),
        )
        self.assertEqual(
            entradas[1][0], "l10n_br_hr_attendance_integridade/models/ptrp_escopo.py"
        )
        self.assertEqual(len(entradas[1][1]), 64)

    def test_modulo_do_escopo_desinstalado_muda_resumo_e_diagnostico(self):
        """Outra composição produz outro resumo, com a ausência explicada."""
        resumo_completo = self.verificador.resumo_fonte()
        instalados = self.verificador._modulos_instalados() - {
            "l10n_br_hr_attendance_afd"
        }
        with patch.object(
            type(self.verificador), "_modulos_instalados", return_value=instalados
        ):
            manifesto = dict(self.verificador._manifesto_fonte())
            # A marca é texto fixo: um terceiro precisa reproduzir o resumo.
            self.assertEqual(
                manifesto["l10n_br_hr_attendance_afd/(modulo nao instalado)"], ""
            )
            self.assertFalse(
                [
                    c
                    for c in manifesto
                    if c.startswith("l10n_br_hr_attendance_afd/models")
                ]
            )
            self.assertNotEqual(self.verificador.resumo_fonte(), resumo_completo)
            texto = self.verificador.texto_do_diagnostico()
        self.assertIn("Módulos do escopo não instalados", texto)
        self.assertIn("l10n_br_hr_attendance_afd", texto)

    def test_modulo_fora_da_lista_autorizada_e_acusado(self):
        """Quem estende modelo atestado sem ser do PTRP vira divergência."""
        autorizados = tuple(
            modulo
            for modulo in ptrp_escopo.MODULOS_DO_PTRP
            if modulo != "l10n_br_hr_attendance_integridade"
        )
        with patch.object(ptrp_escopo, "MODULOS_DO_PTRP", autorizados):
            achados = self.verificador._extensoes_de_terceiros()
        self.assertIn(
            "Modelo l10n_br.hr.apuracao.periodo estendido pelo módulo "
            "l10n_br_hr_attendance_integridade.",
            achados,
        )


@tagged("post_install", "-at_install")
class TestIntegridadeNoAej(TransactionCase):
    """O AEJ gerado carrega a integridade do PTRP vigente naquele momento."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.verificador = cls.env["l10n_br.hr.ptrp.integridade"]
        cls.parametro = cls.env["ir.config_parameter"].sudo()
        # A assinatura do AEJ não é o objeto destes testes.
        patcher = patch.object(
            type(cls.env["l10n_br.hr.apuracao.periodo"]),
            "_certificado_ptrp",
            return_value=None,
        )
        patcher.start()
        cls.addClassCleanup(patcher.stop)
        # Sem contrato não há dia a apurar: o AEJ sai só com cabeçalho,
        # identificação do PTRP e trailer, que basta para a integridade.
        funcionario = cls.env["hr.employee"].create({"name": "Pessoa Sem Contrato"})
        cls.periodo = cls.env["l10n_br.hr.apuracao.periodo"].create(
            {
                "name": "Integridade 03/2026",
                "date_from": date(2026, 3, 2),
                "date_to": date(2026, 3, 3),
                "company_id": cls.env.company.id,
                "employee_ids": [(6, 0, funcionario.ids)],
            }
        )
        cls.periodo.action_apurar()
        cls.periodo.with_context(l10n_br_forcar_fechamento=True).action_fechar()

    def _mensagens_de_integridade(self):
        return [
            corpo
            for corpo in self.periodo.message_ids.mapped("body")
            if "Resumo do escopo atestado" in corpo
        ]

    def test_sem_homologado_carimba_e_avisa_no_chatter(self):
        self.parametro.set_param(PARAM_RESUMO_HOMOLOGADO, "")
        self.periodo.action_gerar_aej()
        self.assertTrue(self.periodo.aej_file)
        self.assertEqual(self.periodo.ptrp_resumo, self.verificador.resumo_fonte())
        self.assertEqual(self.periodo.ptrp_integridade_ok, "nao_configurado")
        self.assertEqual(
            self.periodo.ptrp_diagnostico, self.verificador.texto_do_diagnostico()
        )
        mensagens = self._mensagens_de_integridade()
        self.assertEqual(len(mensagens), 1)
        self.assertIn("Não há resumo homologado", mensagens[0])

    def test_homologado_igual_carimba_sem_alerta(self):
        self.parametro.set_param(
            PARAM_RESUMO_HOMOLOGADO, self.verificador.resumo_fonte()
        )
        self.periodo.action_gerar_aej()
        self.assertEqual(self.periodo.ptrp_integridade_ok, "confere")
        self.assertIn("confere com o homologado", self.periodo.ptrp_diagnostico)
        self.assertFalse(self._mensagens_de_integridade())

    def test_homologado_diferente_carimba_divergencia(self):
        self.parametro.set_param(PARAM_RESUMO_HOMOLOGADO, "f" * 64)
        self.periodo.action_gerar_aej()
        self.assertEqual(self.periodo.ptrp_integridade_ok, "diverge")
        mensagens = self._mensagens_de_integridade()
        self.assertEqual(len(mensagens), 1)
        self.assertIn("DIVERGE do homologado", mensagens[0])

    def test_acao_mostra_o_diagnostico(self):
        self.parametro.set_param(PARAM_RESUMO_HOMOLOGADO, "")
        acao = self.periodo.action_ver_integridade()
        self.assertEqual(acao["tag"], "display_notification")
        self.assertEqual(
            acao["params"]["message"], self.verificador.texto_do_diagnostico()
        )
        self.assertTrue(acao["params"]["sticky"])
