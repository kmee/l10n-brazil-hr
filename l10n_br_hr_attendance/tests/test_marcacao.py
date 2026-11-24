# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Testes da imutabilidade da marcação e da conciliação (RP-03, RP-07)."""

from psycopg2 import IntegrityError

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import PontoCommon


@tagged("post_install", "-at_install")
class TestMarcacao(PontoCommon):
    def test_marcacao_original_nao_pode_ser_alterada(self):
        """Art. 74, IV: nenhum dispositivo pode alterar o registro original."""
        marcacao = self._criar_marcacao(1, self._utc(2026, 3, 2, 11, 0))
        with self.assertRaises(UserError):
            marcacao.write({"datetime_marcacao": self._utc(2026, 3, 2, 12, 0)})
        with self.assertRaises(UserError):
            marcacao.write({"nsr": 999})

    def test_marcacao_nao_pode_ser_excluida(self):
        marcacao = self._criar_marcacao(2, self._utc(2026, 3, 2, 11, 0))
        with self.assertRaises(UserError):
            marcacao.unlink()

    def test_tratamento_permitido_sem_tocar_no_original(self):
        """Pareamento e desconsideração são tratamento, não alteração."""
        marcacao = self._criar_marcacao(3, self._utc(2026, 3, 2, 11, 0))
        marcacao.write({"tipo_marcacao": "E", "seq_par": 1, "state": "tratada"})
        self.assertEqual(marcacao.tipo_marcacao, "E")
        self.assertEqual(marcacao.datetime_marcacao, self._utc(2026, 3, 2, 11, 0))

    def test_desconsideracao_exige_motivo(self):
        marcacao = self._criar_marcacao(4, self._utc(2026, 3, 2, 11, 0))
        with self.assertRaises(UserError):
            marcacao.action_desconsiderar()
        marcacao.action_desconsiderar("Marcação duplicada no relógio")
        self.assertEqual(marcacao.state, "desconsiderada")
        self.assertEqual(marcacao.tipo_marcacao, "D")
        self.assertEqual(marcacao.user_tratamento_id, self.env.user)

    def test_inclusao_manual_exige_motivo(self):
        with self.assertRaises(ValidationError):
            self.env["l10n_br.hr.marcacao"]._criar_marcacoes(
                [
                    {
                        "nsr": 5,
                        "company_id": self.company.id,
                        "employee_id": self.employee.id,
                        "datetime_marcacao": self._utc(2026, 3, 2, 11, 0),
                        "origem": "manual",
                    }
                ]
            )

    @mute_logger("odoo.sql_db")
    def test_nsr_unico_por_rep(self):
        self._criar_marcacao(10, self._utc(2026, 3, 2, 11, 0))
        with self.assertRaises(IntegrityError):
            with self.cr.savepoint():
                self._criar_marcacao(10, self._utc(2026, 3, 2, 12, 0))

    def test_fonte_aej_derivada_da_origem(self):
        """Anexo VI, registro 05: fonteMarc é consequência da origem."""
        original = self._criar_marcacao(11, self._utc(2026, 3, 2, 11, 0))
        self.assertEqual(original.fonte_aej, "O")
        manual = self.env["l10n_br.hr.marcacao"]._criar_marcacoes(
            [
                {
                    "nsr": 12,
                    "company_id": self.company.id,
                    "employee_id": self.employee.id,
                    "datetime_marcacao": self._utc(2026, 3, 2, 13, 0),
                    "origem": "manual",
                    "motivo": "Esquecimento comprovado pelo gestor",
                    "marcacao_origem_id": original.id,
                }
            ]
        )
        self.assertEqual(manual.fonte_aej, "I")
        self.assertEqual(manual.marcacao_origem_id, original)
        self.assertIn(manual, original.tratamento_ids)

    def test_conciliacao_por_cpf(self):
        pendente = self._criar_marcacao(
            20, self._utc(2026, 3, 2, 11, 0), employee=False, cpf="043461292850"
        )
        self.assertFalse(pendente.employee_id)
        encontrado = self.env["hr.employee"]._l10n_br_buscar_por_documento(
            cpf=pendente.cpf
        )
        self.assertEqual(encontrado, self.employee)
        pendente._conciliar_funcionario(encontrado)
        self.assertEqual(pendente.employee_id, self.employee)

    def test_conciliacao_por_pis_quando_cpf_nao_bate(self):
        """Leiaute 1.510 traz PIS, não CPF: o fallback tem que funcionar."""
        encontrado = self.env["hr.employee"]._l10n_br_buscar_por_documento(
            cpf="00000000000", pis="12045678905"
        )
        self.assertEqual(encontrado, self.employee)

    def test_documento_desconhecido_nao_concilia(self):
        encontrado = self.env["hr.employee"]._l10n_br_buscar_por_documento(
            cpf="99999999999"
        )
        self.assertFalse(encontrado)

    def test_troca_de_vinculo_ja_conciliado_e_recusada(self):
        marcacao = self._criar_marcacao(21, self._utc(2026, 3, 2, 11, 0))
        outro = self.env["hr.employee"].create({"name": "Outro Funcionário"})
        with self.assertRaises(UserError):
            marcacao.write({"employee_id": outro.id})

    def test_data_do_dia_usa_fuso_do_funcionario(self):
        """23h em Brasília ainda é o mesmo dia; em UTC já virou."""
        marcacao = self._criar_marcacao(22, self._utc(2026, 3, 3, 2, 0))
        self.assertEqual(str(marcacao.date_marcacao), "2026-03-02")

    def test_hash_encadeia_registros(self):
        """Anexo V, item 9: o hash do anterior entra na base do seguinte."""
        modelo = self.env["l10n_br.hr.marcacao"]
        primeiro = modelo._calcular_hash(
            1,
            "7",
            "2026-03-02T08:00:00-0300",
            "43461292850",
            "2026-03-02T08:00:00-0300",
            "02",
            False,
        )
        segundo = modelo._calcular_hash(
            2,
            "7",
            "2026-03-02T12:00:00-0300",
            "43461292850",
            "2026-03-02T12:00:00-0300",
            "02",
            False,
            hash_anterior=primeiro,
        )
        sem_encadeamento = modelo._calcular_hash(
            2,
            "7",
            "2026-03-02T12:00:00-0300",
            "43461292850",
            "2026-03-02T12:00:00-0300",
            "02",
            False,
        )
        self.assertEqual(len(primeiro), 64)
        self.assertNotEqual(segundo, sem_encadeamento)

    def test_nsr_zero_e_recusado(self):
        """Anexo V: o NSR começa em 1."""
        with self.assertRaisesRegex(ValidationError, "NSR deve iniciar em 1"):
            self._criar_marcacao(0, self._utc(2026, 3, 2, 11, 0))

    def test_marcacao_sem_momento_nao_tem_data(self):
        """Na tela, antes de informar o momento, a data fica vazia."""
        marcacao = self.env["l10n_br.hr.marcacao"].new(
            {"employee_id": self.employee.id, "rep_id": self.rep.id}
        )
        self.assertFalse(marcacao.date_marcacao)

    def test_conciliacao_nao_toca_marcacao_ja_vinculada(self):
        marcacao = self._criar_marcacao(23, self._utc(2026, 3, 2, 11, 0))
        outro = self.env["hr.employee"].create({"name": "Outro Funcionário"})
        conciliadas = marcacao._conciliar_funcionario(outro)
        self.assertFalse(conciliadas)
        self.assertEqual(marcacao.employee_id, self.employee)

    def test_nome_exibido_identifica_a_marcacao(self):
        """O nome aparece no campo de origem do tratamento e na navegação."""
        marcacao = self._criar_marcacao(30, self._utc(2026, 3, 2, 11, 0))
        self.assertEqual(
            marcacao.display_name, "Maria da Silva - 2026-03-02 11:00:00 (NSR 30)"
        )
        pendente = self._criar_marcacao(
            31, self._utc(2026, 3, 2, 12, 0), employee=False, cpf="12345678909"
        )
        self.assertEqual(
            pendente.display_name, "12345678909 - 2026-03-02 12:00:00 (NSR 31)"
        )

    def test_busca_pelo_nome_exibido(self):
        """Busca pelo nome (campo many2one, filtro) não pode travar."""
        marcacao = self._criar_marcacao(32, self._utc(2026, 3, 2, 11, 0))
        pendente = self._criar_marcacao(
            33, self._utc(2026, 3, 2, 12, 0), employee=False, cpf="12345678909"
        )
        Marcacao = self.env["l10n_br.hr.marcacao"]
        self.assertEqual(
            Marcacao.search([("display_name", "ilike", "Maria")]), marcacao
        )
        self.assertEqual(
            Marcacao.search([("display_name", "ilike", "12345678909")]), pendente
        )
