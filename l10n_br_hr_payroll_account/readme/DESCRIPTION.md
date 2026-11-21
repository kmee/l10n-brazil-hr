Integração contábil da folha de pagamento brasileira.

Este módulo estende o `payroll_account` (OCA) para contabilizar as
verbas salariais brasileiras, criando um diário contábil específico para
a folha (FOPAG) e entregando o mapeamento regra-\>conta pronto para uso.

## Mapeamento entregue

Cada regra salarial é ligada a uma conta *lógica* (slot), resolvida no
plano de contas já carregado na empresa: o módulo nunca cria contas. Num
plano brasileiro (`l10n_br_coa_generic`) cada tributo encontra a sua
conta (`INSS a Recolher`, `FGTS a Recolher`, `Férias a Pagar`,
`Encargos Sociais`); num plano genérico tudo cai numa despesa e num
passivo, como antes.

[TABLE]

Como os encargos patronais e as provisões têm os dois lados, o custo do
empregador passa a aparecer no resultado (e a variar conforme o regime
tributário da empresa), sem afetar o líquido do empregado.

O mapeamento é idempotente e não-destrutivo: só preenche contas ainda
vazias, respeitando qualquer configuração manual feita pelo contador.

## Limitação conhecida: contabilização multiempresa

No Odoo 16 os campos `hr.salary.rule.account_debit` / `account_credit`
NÃO são dependentes de empresa, então o mapeamento vale para uma empresa
por vez (a dona do diário FOPAG). Em base multiempresa, as contas das
demais empresas precisam ser configuradas manualmente, e confirmar um
holerite de outra empresa sem essa configuração registraria o custo na
empresa errada.

Para reduzir o risco, o holerite de outra empresa não nasce no diário de
folha desta: quando existe diário na empresa do holerite, ele é usado;
quando não existe, o holerite fica sem contabilização em vez de
contabilizar no lugar errado. É por isso que os lotes de demonstração
por regime tributário ficam calculados e abertos, e não confirmados.
