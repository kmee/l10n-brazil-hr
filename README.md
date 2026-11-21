# l10n-brazil-hr
<!-- /!\ Non OCA Context : Set here the badge of your runbot / runboat instance. -->
[![Pre-commit Status](https://github.com/kmee/l10n-brazil-hr/actions/workflows/pre-commit.yml/badge.svg?branch=18.0)](https://github.com/kmee/l10n-brazil-hr/actions/workflows/pre-commit.yml?query=branch%3A18.0)
[![Build Status](https://github.com/kmee/l10n-brazil-hr/actions/workflows/test.yml/badge.svg?branch=18.0)](https://github.com/kmee/l10n-brazil-hr/actions/workflows/test.yml?query=branch%3A18.0)
[![codecov](https://codecov.io/gh/kmee/l10n-brazil-hr/branch/18.0/graph/badge.svg)](https://codecov.io/gh/kmee/l10n-brazil-hr)
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

Séries disponíveis: 16.0, 17.0, 18.0 (padrão) e 19.0 (só recrutamento). Veja a [arquitetura](docs/ARQUITETURA.md#séries).

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
pip install "odoo-addon-l10n_br_hr_payroll @ git+https://github.com/kmee/l10n-brazil-hr@18.0#subdirectory=l10n_br_hr_payroll"
```

## Documentação

- [Arquitetura](docs/ARQUITETURA.md): como os módulos se encaixam, fluxos e decisões técnicas
- [Como contribuir](docs/CONTRIBUTING.md)
- [Instruções para agentes de IA](AGENTS.md)

<!-- /!\ do not modify below this line -->

<!-- prettier-ignore-start -->

[//]: # (addons)

## Módulos

### Folha de pagamento

Módulo | Versão | Descrição
--- | --- | ---
[l10n_br_hr_payroll](l10n_br_hr_payroll/) | 18.0.1.0.0 | Regras salariais brasileiras: INSS, IRRF, FGTS, adicionais, encargos patronais por regime tributário e provisões
[l10n_br_hr_payroll_account](l10n_br_hr_payroll_account/) | 18.0.1.0.0 | Contabilização do holerite
[l10n_br_hr_payroll_report](l10n_br_hr_payroll_report/) | 18.0.1.0.0 | Holerite com layout brasileiro
[l10n_br_hr_benefit](l10n_br_hr_benefit/) | 18.0.1.0.0 | Benefícios: vale-transporte, vale-refeição, vale-alimentação e plano de saúde
[l10n_br_hr_holiday](l10n_br_hr_holiday/) | 18.0.1.0.0 | Tipos de afastamento e faltas da CLT
[l10n_br_hr_vacation](l10n_br_hr_vacation/) | 18.0.1.0.0 | Férias, abono pecuniário, 13º salário e rescisão
[l10n_br_hr_substituicao](l10n_br_hr_substituicao/) | 18.0.1.0.0 | Substituição temporária de funcionários (CLT, art. 450)
[l10n_br_hr_syndicate](l10n_br_hr_syndicate/) | 18.0.1.0.0 | Sindicato do contrato
[l10n_br_hr_validacao_folha](l10n_br_hr_validacao_folha/) | 18.0.1.0.0 | Validações do holerite
[l10n_br_hr_gerador_holerite](l10n_br_hr_gerador_holerite/) | 18.0.1.0.0 | Geração em lote de holerites para simulação
[l10n_br_ressarcimento](l10n_br_ressarcimento/) | 18.0.1.0.0 | Reembolso de despesas do empregado pelo holerite
[l10n_br_ressarcimento_account](l10n_br_ressarcimento_account/) | 18.0.1.0.0 | Contabilização do reembolso pelo holerite
[l10n_br_hr_arquivos_governo](l10n_br_hr_arquivos_governo/) | 18.0.1.0.0 | Descontinuado: SEFIP, DIRF e CAGED (mantido só para consulta)

### eSocial

Módulo | Versão | Descrição
--- | --- | ---
[l10n_br_esocial](l10n_br_esocial/) | 18.0.1.1.0 | Eventos e lotes do eSocial (S-1.3), ciclo até a DCTFWeb e totalizadores
[l10n_br_esocial_sst](l10n_br_esocial_sst/) | 18.0.1.0.0 | Eventos de SST do eSocial: S-2210, S-2220, S-2221 e S-2240

### Saúde e Segurança do Trabalho

Módulo | Versão | Descrição
--- | --- | ---
[l10n_br_hr_sst](l10n_br_hr_sst/) | 18.0.1.0.0 | Inventário de riscos ocupacionais
[l10n_br_hr_sst_epi](l10n_br_hr_sst_epi/) | 18.0.1.0.0 | Entrega de EPI (NR-6)
[l10n_br_hr_sst_aso](l10n_br_hr_sst_aso/) | 18.0.1.0.0 | Exames ocupacionais e PCMSO (NR-7)
[l10n_br_hr_sst_cat](l10n_br_hr_sst_cat/) | 18.0.1.0.0 | Acidente de trabalho e CAT
[l10n_br_hr_payroll_sst](l10n_br_hr_payroll_sst/) | 18.0.1.0.0 | Insalubridade e periculosidade na folha a partir do laudo

### Ponto eletrônico

Módulo | Versão | Descrição
--- | --- | ---
[l10n_br_hr_attendance](l10n_br_hr_attendance/) | 18.0.1.0.0 | Base do registro de ponto (Portaria MTP 671/2021)
[l10n_br_hr_attendance_afd](l10n_br_hr_attendance_afd/) | 18.0.1.0.0 | Importação e geração do AFD
[l10n_br_hr_attendance_apuracao](l10n_br_hr_attendance_apuracao/) | 18.0.1.0.0 | Apuração da jornada pelas regras da CLT
[l10n_br_hr_attendance_aej](l10n_br_hr_attendance_aej/) | 18.0.1.0.0 | AEJ e espelho de ponto
[l10n_br_hr_attendance_integridade](l10n_br_hr_attendance_integridade/) | 18.0.1.0.0 | Integridade do programa de tratamento de ponto
[l10n_br_hr_payroll_attendance](l10n_br_hr_payroll_attendance/) | 18.0.1.0.0 | Ponto no holerite: dias trabalhados, horas extras e faltas
[l10n_br_hr_holidays_public](l10n_br_hr_holidays_public/) | 18.0.1.0.0 | Importação dos feriados brasileiros
[l10n_br_hr_overtime_custom_multiplier](l10n_br_hr_overtime_custom_multiplier/) | 18.0.1.0.0 | Multiplicador de horas extras por faixa
[hr_overtime_report_action_pdf](hr_overtime_report_action_pdf/) | 18.0.1.0.0 | Relatório PDF das horas extras

### Recrutamento

Módulo | Versão | Descrição
--- | --- | ---
[l10n_br_hr_recruitment](l10n_br_hr_recruitment/) | 18.0.1.0.0 | Dados brasileiros do candidato, levados ao funcionário
[l10n_br_website_hr_recruitment_form](l10n_br_website_hr_recruitment_form/) | 18.0.1.0.0 | Formulário público para o candidato completar os dados

### Técnico

Módulo | Versão | Descrição
--- | --- | ---
[l10n_br_hr_setup_tests](l10n_br_hr_setup_tests/) | 18.0.1.0.0 | Plano de contas das empresas de demonstração no CI (não instalar em produção)

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
