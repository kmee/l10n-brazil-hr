# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from unittest import mock

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from erpbrasil.assinatura.certificado import Certificado
from esociallib.exceptions import EsocialTransmissionError
from lxml import etree

from odoo.exceptions import UserError

from .common import (
    RECIBO_S1200,
    ESocialCicloCommon,
    FakeEventoResult,
    FakeLoteResult,
)

LOTE_MODULE = "odoo.addons.l10n_br_esocial.models.esocial_lote"
PROTOCOLO = "1.2.202403.0000000000000000001"
NS_DS = "{http://www.w3.org/2000/09/xmldsig#}"


def _xml_evento(id_evento):
    return (
        '<eSocial xmlns="http://www.esocial.gov.br/schema/evt/evtRemun/v_S_01_03_00">'
        f'<evtRemun Id="{id_evento}"/></eSocial>'
    )


def _pfx_autoassinado(senha):
    """Certificado A1 autoassinado gerado no teste (PKCS#12 e o X.509)."""
    chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "Certificado de Teste eSocial")]
    )
    agora = datetime.now(timezone.utc)
    certificado = (
        x509.CertificateBuilder()
        .subject_name(nome)
        .issuer_name(nome)
        .public_key(chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - timedelta(days=1))
        .not_valid_after(agora + timedelta(days=30))
        .sign(chave, hashes.SHA256())
    )
    pfx = pkcs12.serialize_key_and_certificates(
        b"teste",
        chave,
        certificado,
        None,
        serialization.BestAvailableEncryption(senha.encode()),
    )
    return pfx, certificado


def _assinar(xml, pfx_data, senha):
    """Assinatura simulada: devolve o XML com o grupo Signature."""
    return xml.replace("</eSocial>", "<Signature/></eSocial>")


class TestESocialLoteTransmissao(ESocialCicloCommon):
    """Envio e consulta do lote com o webservice do eSocial simulado."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Lote = cls.env["l10n_br.esocial.lote"]

    def _evento(self, id_evento, tipo="S-1200", state="validated", **kwargs):
        vals = {
            "id_evento": id_evento,
            "xml_envio": _xml_evento(id_evento),
            "per_apur": "2024-03",
        }
        vals.update(kwargs)
        return self._criar_evento(tipo, state=state, **vals)

    def _lote(self, eventos, **vals):
        lote = self.Lote.create(dict({"company_id": self.company.id}, **vals))
        eventos.write({"lote_id": lote.id})
        return lote

    def _webservice(self, **patches):
        """Simula o certificado e a esociallib (assinatura e webservice)."""
        stack = ExitStack()
        stack.enter_context(
            mock.patch.object(
                type(self.Lote), "_get_certificate", return_value=(b"pfx", "senha")
            )
        )
        for nome, valor in patches.items():
            stack.enter_context(mock.patch(f"{LOTE_MODULE}.{nome}", valor))
        return stack

    # -- Transmissão ---------------------------------------------------------

    def test_transmitir_assina_e_registra_protocolo(self):
        eventos = self._evento("ID1") | self._evento("ID2")
        rascunho = self._evento("ID3", state="draft")
        lote = self._lote(eventos | rascunho)
        enviar = mock.Mock(return_value=PROTOCOLO)
        with self._webservice(assinar=_assinar, enviar_lote=enviar):
            acao = lote.action_transmitir()

        enviar.assert_called_once()
        xmls, pfx, senha = enviar.call_args.args
        self.assertEqual(len(xmls), 2)
        self.assertTrue(all("<Signature/>" in xml for xml in xmls))
        self.assertEqual((pfx, senha), (b"pfx", "senha"))
        self.assertEqual(enviar.call_args.kwargs["environment"], "restricted")
        self.assertEqual(enviar.call_args.kwargs["grupo"], 3)
        self.assertEqual(lote.state, "sent")
        self.assertEqual(lote.protocolo, PROTOCOLO)
        self.assertEqual(lote.name, f"Lote {PROTOCOLO}")
        self.assertEqual(set(eventos.mapped("state")), {"sent"})
        self.assertIn("<Signature/>", eventos[0].xml_envio)
        # Só os eventos validados seguem no envio.
        self.assertEqual(rascunho.state, "draft")
        self.assertNotIn("<Signature/>", rascunho.xml_envio)
        self.assertEqual(acao["params"]["message"], f"Protocolo: {PROTOCOLO}")

    def test_transmitir_tabelas_em_producao(self):
        self.company.l10n_br_esocial_tp_amb = "1"
        eventos = self._evento("ID1", tipo="S-1000") | self._evento(
            "ID2", tipo="S-1010"
        )
        lote = self._lote(eventos)
        enviar = mock.Mock(return_value=PROTOCOLO)
        with self._webservice(assinar=_assinar, enviar_lote=enviar):
            lote.action_transmitir()
        self.assertEqual(enviar.call_args.kwargs["environment"], "production")
        self.assertEqual(enviar.call_args.kwargs["grupo"], 1)

    def test_erro_de_comunicacao_nao_grava_nada(self):
        """Falha no webservice desfaz a assinatura e mantém o lote em rascunho."""
        evento = self._evento("ID1")
        xml_original = evento.xml_envio
        lote = self._lote(evento)
        enviar = mock.Mock(side_effect=EsocialTransmissionError("tempo esgotado"))
        with self._webservice(assinar=_assinar, enviar_lote=enviar):
            with self.assertRaises(UserError) as erro:
                lote.action_transmitir()
        self.assertIn("Falha na assinatura/transmissão do lote", str(erro.exception))
        self.assertIn("tempo esgotado", str(erro.exception))
        self.assertEqual(lote.state, "draft")
        self.assertFalse(lote.protocolo)
        self.assertEqual(evento.state, "validated")
        self.assertEqual(evento.xml_envio, xml_original)

    def test_evento_sem_xml_nao_e_assinado(self):
        evento = self._evento("ID1", xml_envio=False)
        lote = self._lote(evento)
        assinar = mock.Mock(side_effect=_assinar)
        enviar = mock.Mock(return_value=PROTOCOLO)
        with self._webservice(assinar=assinar, enviar_lote=enviar):
            with self.assertRaises(UserError) as erro:
                lote.action_transmitir()
        self.assertIn("não possui XML de envio", str(erro.exception))
        assinar.assert_not_called()
        enviar.assert_not_called()
        self.assertEqual(lote.state, "draft")

    def test_transmitir_valida_o_lote(self):
        evento_model = self.env["l10n_br.esocial.evento"]
        casos = [
            ("lote enviado", "sent", self._evento("IDA"), "Apenas lotes em rascunho"),
            ("lote vazio", "draft", evento_model, "O lote não possui eventos"),
            (
                "sem evento validado",
                "draft",
                self._evento("IDB", state="draft"),
                "Nenhum evento validado",
            ),
            (
                "grupos misturados",
                "draft",
                self._evento("IDC", tipo="S-1000") | self._evento("IDD"),
                "1-Tabelas, 3-Periódicos",
            ),
        ]
        enviar = mock.Mock(return_value=PROTOCOLO)
        with self._webservice(assinar=_assinar, enviar_lote=enviar):
            for rotulo, estado, eventos, mensagem in casos:
                with self.subTest(rotulo):
                    lote = self._lote(eventos, state=estado)
                    with self.assertRaises(UserError) as erro:
                        lote.action_transmitir()
                    self.assertIn(mensagem, str(erro.exception))
        enviar.assert_not_called()

    def test_maximo_50_eventos_por_lote(self):
        eventos = self.env["l10n_br.esocial.evento"].create(
            [
                {
                    "tipo": "S-1200",
                    "company_id": self.company.id,
                    "state": "validated",
                    "xml_envio": _xml_evento(f"ID{i}"),
                }
                for i in range(51)
            ]
        )
        lote = self._lote(eventos)
        enviar = mock.Mock(return_value=PROTOCOLO)
        with self._webservice(assinar=_assinar, enviar_lote=enviar):
            with self.assertRaises(UserError) as erro:
                lote.action_transmitir()
        self.assertIn(
            "Máximo 50 eventos por lote (51 encontrados)", str(erro.exception)
        )
        enviar.assert_not_called()

    def test_esociallib_sem_transmissao(self):
        """Sem o erpbrasil, a esociallib expõe assinar e enviar como None."""
        lote = self._lote(self._evento("ID1"))
        with self._webservice(assinar=None, enviar_lote=None):
            with self.assertRaises(UserError) as erro:
                lote.action_transmitir()
        self.assertIn("esociallib não está instalada", str(erro.exception))
        lote.write({"state": "sent", "protocolo": PROTOCOLO})
        with self._webservice(consultar_lote=None):
            with self.assertRaises(UserError) as erro:
                lote.action_consultar()
        self.assertIn("esociallib não está instalada", str(erro.exception))

    def test_transmitir_com_o_certificado_da_empresa(self):
        """O certificado do l10n_br_fiscal_certificate chega à esociallib.

        ``res.company._get_br_ecertificate`` devolve um
        ``erpbrasil.assinatura.certificado.Certificado``. O evento é assinado
        de verdade pela esociallib e o envio recebe o PKCS#12 e a senha que
        reabrem o mesmo certificado.
        """
        senha = "senha-de-teste"
        pfx, cert_x509 = _pfx_autoassinado(senha)
        certificado = Certificado(arquivo=base64.b64encode(pfx), senha=senha)
        evento = self._evento("ID1")
        lote = self._lote(evento)
        enviar = mock.Mock(return_value=PROTOCOLO)
        with (
            mock.patch.object(
                type(self.company),
                "_get_br_ecertificate",
                create=True,
                return_value=certificado,
            ),
            mock.patch(f"{LOTE_MODULE}.enviar_lote", enviar),
        ):
            lote.action_transmitir()

        (xml_assinado,), cert_pfx, cert_password = enviar.call_args.args
        reaberto = Certificado(arquivo=cert_pfx, senha=cert_password)
        self.assertEqual(reaberto.cert, cert_x509)
        self.assertEqual(lote.state, "sent")
        self.assertEqual(evento.xml_envio, xml_assinado)

        # Assinatura com a chave do certificado da empresa.
        raiz = etree.fromstring(xml_assinado.encode())
        der = cert_x509.public_bytes(serialization.Encoding.DER)
        x509_xml = raiz.find(f".//{NS_DS}X509Certificate").text
        self.assertEqual(base64.b64decode(x509_xml), der)
        signed_info = etree.tostring(raiz.find(f".//{NS_DS}SignedInfo"), method="c14n")
        assinatura = base64.b64decode(raiz.find(f".//{NS_DS}SignatureValue").text)
        cert_x509.public_key().verify(
            assinatura, signed_info, padding.PKCS1v15(), hashes.SHA1()
        )

    def test_certificado_nao_configurado(self):
        if hasattr(self.company, "_get_br_ecertificate"):
            self.skipTest("l10n_br_fiscal_certificate instalado")
        lote = self._lote(self._evento("ID1"))
        with self.assertRaises(UserError) as erro:
            lote._get_certificate()
        self.assertIn("Certificado digital A1 não configurado", str(erro.exception))
        self.assertIn(self.company.name, str(erro.exception))

    # -- Consulta ------------------------------------------------------------

    def _consultar(self, lote, resultado):
        consultar = mock.Mock(return_value=resultado)
        with self._webservice(consultar_lote=consultar):
            acao = lote.action_consultar()
        consultar.assert_called_once_with(
            PROTOCOLO, b"pfx", "senha", environment="restricted"
        )
        return acao

    def _lote_enviado(self, *ids):
        eventos = self.env["l10n_br.esocial.evento"]
        for id_evento in ids:
            eventos |= self._evento(id_evento, state="sent")
        return self._lote(eventos, state="sent", protocolo=PROTOCOLO), eventos

    def test_consulta_registra_aceite_e_recusa(self):
        """Recusa do fisco é resultado gravado no lote, não exceção."""
        lote, (aceito, recusado, recusado_sem_xml) = self._lote_enviado(
            "ID1", "ID2", "ID3"
        )
        # Evento de outro lote com Id igual ao de um retorno estranho a este.
        outro_lote, outro = self._lote_enviado("IDOUTRO")
        retorno_recusa = "<retornoEvento><cdResposta>401</cdResposta></retornoEvento>"
        resultado = FakeLoteResult(
            status="processado",
            eventos=[
                FakeEventoResult("ID1", aceito=True, nr_recibo=RECIBO_S1200),
                FakeEventoResult(
                    "ID2",
                    aceito=False,
                    code="1110",
                    description="Valor da rubrica divergente",
                    retorno_xml=retorno_recusa,
                ),
                FakeEventoResult("ID3", aceito=False),
                FakeEventoResult("IDOUTRO", aceito=True, nr_recibo=RECIBO_S1200),
            ],
        )
        acao = self._consultar(lote, resultado)

        self.assertEqual(aceito.state, "success")
        self.assertEqual(aceito.nr_recibo, RECIBO_S1200)
        self.assertFalse(aceito.ocorrencia_ids)

        self.assertEqual(recusado.state, "error")
        self.assertEqual(recusado.xml_retorno, retorno_recusa)
        self.assertFalse(recusado.nr_recibo)
        self.assertEqual(recusado.ocorrencia_ids.codigo, "1110")
        self.assertEqual(
            recusado.ocorrencia_ids.descricao, "Valor da rubrica divergente"
        )
        self.assertEqual(recusado.ocorrencia_ids.tipo, "1")

        self.assertEqual(recusado_sem_xml.state, "error")
        self.assertFalse(recusado_sem_xml.xml_retorno)
        self.assertEqual(len(recusado_sem_xml.ocorrencia_ids), 1)
        self.assertFalse(recusado_sem_xml.ocorrencia_ids.codigo)

        # O retorno só casa com eventos do próprio lote.
        self.assertEqual(outro.state, "sent")
        self.assertFalse(outro.nr_recibo)
        self.assertEqual(outro_lote.state, "sent")

        self.assertEqual(lote.state, "error")
        self.assertEqual(acao["params"]["message"], "Status: processado")
        self.assertEqual(acao["params"]["type"], "info")

    def test_consulta_com_todos_aceitos_conclui_o_lote(self):
        lote, evento = self._lote_enviado("ID1")
        resultado = FakeLoteResult(
            eventos=[FakeEventoResult("ID1", aceito=True, nr_recibo=RECIBO_S1200)]
        )
        self._consultar(lote, resultado)
        self.assertEqual(lote.state, "done")
        self.assertEqual(evento.state, "success")

    def test_consulta_em_processamento(self):
        lote, evento = self._lote_enviado("ID1")
        self._consultar(lote, FakeLoteResult(status="em_processamento"))
        self.assertEqual(lote.state, "processing")
        self.assertEqual(evento.state, "sent")

    def test_consulta_com_lote_rejeitado(self):
        """Lote rejeitado inteiro: o lote vai a erro e os eventos ficam enviados."""
        lote, evento = self._lote_enviado("ID1")
        acao = self._consultar(lote, FakeLoteResult(status="erro"))
        self.assertEqual(lote.state, "error")
        self.assertEqual(evento.state, "sent")
        self.assertFalse(evento.ocorrencia_ids)
        self.assertEqual(acao["params"]["type"], "danger")

    def test_consulta_com_erro_de_comunicacao_nao_grava_nada(self):
        """Falha no webservice vira UserError e o lote segue enviado."""
        lote, evento = self._lote_enviado("ID1")
        consultar = mock.Mock(side_effect=EsocialTransmissionError("tempo esgotado"))
        with self._webservice(consultar_lote=consultar):
            with self.assertRaises(UserError) as erro:
                lote.action_consultar()
        self.assertIn("Falha na consulta do lote", str(erro.exception))
        self.assertIn("tempo esgotado", str(erro.exception))
        self.assertEqual(lote.state, "sent")
        self.assertEqual(lote.protocolo, PROTOCOLO)
        self.assertEqual(evento.state, "sent")
        self.assertFalse(evento.ocorrencia_ids)

    def test_consulta_exige_protocolo(self):
        lote = self._lote(self._evento("ID1", state="sent"), state="sent")
        consultar = mock.Mock()
        with self._webservice(consultar_lote=consultar):
            with self.assertRaises(UserError) as erro:
                lote.action_consultar()
        self.assertIn("Lote sem protocolo", str(erro.exception))
        consultar.assert_not_called()

    # -- Estado e nome -------------------------------------------------------

    def test_lote_em_rascunho_nao_volta_a_rascunho(self):
        lote = self._lote(self._evento("ID1"))
        with self.assertRaises(UserError):
            lote.action_reset_draft()
        lote.state = "error"
        lote.action_reset_draft()
        self.assertEqual(lote.state, "draft")

    def test_nome_do_lote(self):
        self.assertEqual(self.Lote.new({}).name, "Lote Novo")
        lote = self._lote(self._evento("ID1"))
        self.assertEqual(
            lote.name, f"Lote {lote.create_date.strftime('%Y-%m-%d %H:%M')}"
        )
