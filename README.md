# l10n-brazil-hr
<!-- /!\ Non OCA Context : Set here the badge of your runbot / runboat instance. -->
[![Pre-commit Status](https://github.com/kmee/l10n-brazil-hr/actions/workflows/pre-commit.yml/badge.svg?branch=19.0)](https://github.com/kmee/l10n-brazil-hr/actions/workflows/pre-commit.yml?query=branch%3A19.0)
[![Build Status](https://github.com/kmee/l10n-brazil-hr/actions/workflows/test.yml/badge.svg?branch=19.0)](https://github.com/kmee/l10n-brazil-hr/actions/workflows/test.yml?query=branch%3A19.0)
[![codecov](https://codecov.io/gh/kmee/l10n-brazil-hr/branch/19.0/graph/badge.svg)](https://codecov.io/gh/kmee/l10n-brazil-hr)
<!-- /!\ Non OCA Context : Set here the badge of your translation instance. -->

<!-- /!\ do not modify above this line -->

Recursos Humanos da localização brasileira do Odoo: folha de pagamento, eSocial, Saúde e
Segurança do Trabalho (SST), ponto eletrônico, férias e 13º salário, benefícios e recrutamento.

Este repositório complementa o [OCA/l10n-brazil](https://github.com/OCA/l10n-brazil), o
repositório principal da localização brasileira. O cadastro de RH (`l10n_br_hr`,
`l10n_br_hr_contract`), a base fiscal (`l10n_br_fiscal`) e os feriados (`l10n_br_resource`) vêm de
lá; aqui ficam os módulos que constroem a operação de RH em cima deles. A folha genérica vem do
[OCA/payroll](https://github.com/OCA/payroll).

Repositório irmão, no mesmo modelo:
[kmee/l10n-brazil-fiscal-contrib](https://github.com/kmee/l10n-brazil-fiscal-contrib) (grupos de
nicho dos documentos fiscais).

Nesta série (19.0) só existem os módulos de recrutamento: o OCA/l10n-brazil 19.0 ainda não tem o `l10n_br_hr_contract`, de que dependem a folha, o eSocial, a SST e o ponto. Veja a [arquitetura](docs/ARQUITETURA.md#séries).

## Por que um repositório separado

O RH tem dependências e um calendário regulatório próprios (eSocial, Portaria MTP 671/2021,
normas regulamentadoras). Num repositório só dele, o CI instala e testa apenas o RH, quem precisa
só de RH agrega só RH, e os módulos seguem o template da OCA para poderem ser propostos a ela. O
detalhe está na [arquitetura](docs/ARQUITETURA.md#por-que-um-repositório-separado).

## Instalação

Agregue a branch da série junto com as dependências:

- [OCA/l10n-brazil](https://github.com/OCA/l10n-brazil)
- [OCA/payroll](https://github.com/OCA/payroll)
- [OCA/hr](https://github.com/OCA/hr) e [OCA/hr-holidays](https://github.com/OCA/hr-holidays)

Cada módulo também pode ser instalado com o pip direto do git, por exemplo:

```bash
pip install "odoo-addon-l10n_br_hr_payroll @ git+https://github.com/kmee/l10n-brazil-hr@19.0#subdirectory=l10n_br_hr_payroll"
```

## Documentação

- [Arquitetura](docs/ARQUITETURA.md): como os módulos se encaixam, fluxos e decisões técnicas
- [Como contribuir](docs/CONTRIBUTING.md)
- [Instruções para agentes de IA](AGENTS.md)

<!-- /!\ do not modify below this line -->

<!-- prettier-ignore-start -->

[//]: # (addons)

## Módulos

### Recrutamento

Módulo | Versão | Descrição
--- | --- | ---
[l10n_br_hr_recruitment](l10n_br_hr_recruitment/) | 19.0.1.0.0 | Dados brasileiros do candidato, levados ao funcionário
[l10n_br_website_hr_recruitment_form](l10n_br_website_hr_recruitment_form/) | 19.0.1.0.0 | Formulário público para o candidato completar os dados

[//]: # (end addons)

<!-- prettier-ignore-end -->

## Licenças

Este repositório é licenciado sob a [AGPL-3.0](LICENSE).

Cada módulo pode ter licença própria, desde que siga a política da Odoo Community Association
(OCA). Consulte a chave `license` do `__manifest__.py` de cada módulo.

----
<!-- /!\ Non OCA Context : Set here the full description of your organization. -->
Mantido pela [KMEE](https://kmee.com.br), contribuidora da
[OCA](https://odoo-community.org/) e da localização brasileira do Odoo.
