Módulo técnico para o CI deste repositório. Não deve ser instalado em bases de produção.

O CI instala só os módulos deste repositório e as suas dependências. Sem um módulo de plano de
contas brasileiro, as empresas de demonstração do `l10n_br_base` ficam sem plano de contas, e
qualquer teste que crie fatura, lançamento contábil ou contabilize um holerite nelas falha. Ao
depender do `l10n_br_coa_generic`, o módulo carrega o plano brasileiro nas empresas de
demonstração, como no CI do OCA/l10n-brazil.
