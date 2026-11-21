# Como contribuir

Contribuições são bem-vindas: correção de cálculo, evento novo do eSocial, porte entre séries,
testes, tradução e documentação. Este repositório segue as convenções da
[OCA](https://odoo-community.org/), para que os módulos possam ser propostos a ela sem retrabalho.

## Antes de começar

- Leia a [arquitetura](ARQUITETURA.md), em especial a seção "O que fica no OCA/l10n-brazil": campo
  ou validação do cadastro do funcionário, do contrato ou da empresa vai para o
  [OCA/l10n-brazil](https://github.com/OCA/l10n-brazil), não para cá.
- Procure uma issue ou PR aberto sobre o mesmo assunto. Se não houver e a mudança for grande, abra
  uma issue descrevendo o problema antes do código.
- Escolha a série certa: cada versão do Odoo tem a sua branch (`16.0`, `17.0`, `18.0`, `19.0`).
  Correção que vale para várias séries entra primeiro na mais antiga em que o módulo existe e é
  portada para as seguintes.

## Fluxo

1. Faça um fork e crie a branch a partir da série: `<série>-<tipo>-<módulo>-<assunto>`, por
   exemplo `18.0-fix-l10n_br_hr_payroll-irrf-redutor`.
2. Um PR por módulo sempre que possível. Título no padrão da OCA:
   `[18.0][FIX] l10n_br_hr_payroll: redutor do IRRF a partir de 2026`.
3. Commits com a etiqueta da OCA no início (`[ADD]`, `[FIX]`, `[IMP]`, `[REF]`, `[MIG]`, `[REM]`)
   seguida do módulo e de um resumo curto. O corpo explica o porquê da mudança.
4. Este repositório não tem o bot da OCA que sobe a versão no merge: quem abre o PR sobe a versão
   do módulo no `__manifest__.py` (terceiro número para correção, segundo para funcionalidade) e
   acrescenta o script em `migrations/` quando a mudança altera dados já gravados.
5. O PR é mesclado com o CI verde (pre-commit e testes).

## Qualidade

### pre-commit

O pre-commit roda os mesmos linters da OCA (ruff, pylint-odoo, prettier, geração dos READMEs):

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

Não edite à mão o `README.rst` dos módulos, o `static/description/index.html` nem os `.pot`: são
gerados.

### Testes

Todo comportamento novo ou corrigido vem com teste que falha sem a mudança. O CI usa a imagem da
OCA; para reproduzir localmente numa cópia do repositório (clone, não worktree):

```bash
docker run --rm -v "$PWD":/work -w /work ghcr.io/oca/oca-ci/py3.10-odoo18.0:latest \
  sh -c "oca_install_addons && oca_init_test_database && oca_run_tests"
```

A imagem precisa de um PostgreSQL acessível (veja as variáveis `PG*` no
[oca-ci](https://github.com/OCA/oca-ci)). O `oca_install_addons` grava `test-requirements.txt` e
`test-constraints.txt` temporários; descarte essas alterações antes de commitar.

Os testes rodam com o plano de contas brasileiro carregado (módulo técnico
`l10n_br_hr_setup_tests`). Teste que procura conta pelo nome ou pelo código precisa funcionar
com esse plano.

## Documentação dos módulos

- Cada módulo descreve o que faz em `readme/DESCRIPTION.md`, em português, como no
  OCA/l10n-brazil. `USAGE.md`, `CONFIGURE.md` e `ROADMAP.md` quando fizerem sentido.
- `readme/CONTRIBUTORS.md` lista quem escreveu o módulo; acrescente o seu nome quando contribuir.
- Regra legal ou de cálculo cita a fonte (lei, artigo, portaria, NR, leiaute do eSocial).

## Dados pessoais e segredos

Folha e eSocial lidam com CPF, salário, saúde e acidente de trabalho. Em teste, demo, issue e PR:

- use CPF, PIS e CNPJ gerados para teste, nunca de pessoas ou empresas reais;
- nunca inclua certificado digital, senha, token ou XML transmitido de uma empresa real;
- ao anexar log ou XML de erro, remova os dados pessoais antes.

## Uso de inteligência artificial

O repositório segue a [política de IA da OCA](https://www.odoo-community.org/blog/news-updates-1/new-ai-policy-248):
quem abre o PR é o autor e responde pelo código, mesmo que uma ferramenta tenha ajudado. Commit
feito com ajuda de IA leva o trailer `Assisted-by: <ferramenta>`; nunca `Co-authored-by` de IA. As
instruções para agentes estão no [AGENTS.md](../AGENTS.md).

## Licença

Ao contribuir, você concorda em licenciar a contribuição sob a
[AGPL-3.0](../LICENSE), a mesma dos módulos.
