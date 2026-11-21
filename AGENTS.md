# Instruções para agentes de IA

Este arquivo orienta agentes de IA (Codex, Claude Code e similares) que trabalham neste
repositório. O `CLAUDE.md` é um link simbólico para ele: edite só este arquivo. As
mesmas regras valem para pessoas; o detalhe está em
[docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) e
[docs/ARQUITETURA.md](docs/ARQUITETURA.md).

## O que é este repositório

Addons Odoo de Recursos Humanos da localização brasileira (folha, eSocial, SST, ponto
eletrônico, férias, benefícios, recrutamento), em cima do
[OCA/l10n-brazil](https://github.com/OCA/l10n-brazil) e do
[OCA/payroll](https://github.com/OCA/payroll). Segue o template da OCA: uma pasta por
módulo na raiz, uma branch por série (`16.0`, `17.0`, `18.0`, `19.0`), sem branch
`main`.

## Antes de mudar código

1. Confirme a série. O código de uma série usa a API do Odoo daquela versão; não traga
   sintaxe de versão mais nova para uma série antiga.
2. Leia o `__manifest__.py` e o `readme/DESCRIPTION.md` do módulo, e a seção "O que fica
   no OCA/l10n-brazil" da arquitetura. Campo ou validação do cadastro do funcionário, do
   contrato ou da empresa pertence ao OCA/l10n-brazil: não crie aqui um campo que
   duplique um de lá.
3. Verifique quem depende do módulo (`grep -l '"<módulo>"' */__manifest__.py`). Quase
   tudo depende de `l10n_br_hr_payroll`; mudança nele afeta a folha inteira.

## Comandos

```bash
pre-commit run --all-files                       # linters da OCA; rode antes de commitar
pre-commit run --files <arquivos>                # só os arquivos alterados
```

Testes rodam no CI (imagem `ghcr.io/oca/oca-ci`). Para reproduzir localmente, veja
[docs/CONTRIBUTING.md](docs/CONTRIBUTING.md#testes). Um teste novo deve falhar sem a
mudança que ele cobre.

## Convenções

- **Commits**: etiqueta da OCA (`[ADD]`, `[FIX]`, `[IMP]`, `[REF]`, `[MIG]`), módulo,
  resumo curto; o corpo explica o porquê. Commit feito com ajuda de IA leva
  `Assisted-by: <ferramenta>`; nunca `Co-authored-by` de IA (política de IA da OCA).
- **PR**: um por módulo sempre que possível, título
  `[<série>][<TAG>] <módulo>: <resumo>`.
- **Versão**: não há bot de merge; quem muda o módulo sobe a versão no manifesto e
  escreve o script em `migrations/` quando dados gravados mudam.
- **README**: texto em português nos fragmentos de `readme/`. Não edite à mão
  `README.rst`, `static/description/index.html` nem `.pot`: são gerados.
- **Texto**: sem travessão nem aspas curvas; use vírgula, dois-pontos ou parênteses.

## Regras do domínio

- **CPF e PIS só com dígitos.** Desde a 18.0 o `l10n_br_hr` grava os documentos do
  funcionário sem pontuação. Formate só na exibição
  (`erpbrasil.base.fiscal.cnpj_cpf.formata`). O CPF do funcionário vem do contato de
  trabalho; não assuma que o contato é do Brasil.
- **eSocial.** O domínio válido de cada campo (tabelas, enumerações) vem dos bindings da
  `esociallib`, gerados dos XSD oficiais. Confira lá antes de escrever uma `Selection`;
  não use memória nem documento secundário.
- **Critério legal com fonte.** Alíquota, faixa, prazo ou regra de cálculo cita a norma
  (lei, artigo, portaria, NR) no código ou no README. Valores que mudam no tempo ficam
  em tabela com vigência.
- **Encargos por regime.** O custo patronal depende do regime tributário da empresa
  (`l10n_br_fiscal`); teste os regimes afetados (Lucro Real ou Presumido, Simples por
  anexo, CPRB), não só um.
- **Testes com plano brasileiro.** O CI carrega o plano de contas brasileiro
  (`l10n_br_hr_setup_tests`). Teste que procura conta pelo nome ou código precisa
  funcionar com ele.

## O que não fazer

- Não use dados reais: CPF, PIS, CNPJ, nomes, salários, certificados, senhas, tokens ou
  XML de empresas e pessoas reais não entram em código, teste, demo, issue, PR nem log.
  Use documentos gerados para teste.
- Não relaxe validação, regra de segurança (`ir.rule`, grupos) ou teste para o CI
  passar: corrija a causa.
- Não altere os arquivos gerados pelo template da OCA (`.pre-commit-config.yaml`,
  `.github/`, `.pylintrc*`, `.ruff.toml`) sem necessidade explícita; quando alterar,
  explique no commit.
- Não misture no mesmo PR mudanças de módulos ou de séries diferentes.
