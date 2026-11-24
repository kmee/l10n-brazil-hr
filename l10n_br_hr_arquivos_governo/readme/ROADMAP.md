O módulo não recebe mais desenvolvimento de geradores. O código de
montagem dos três leiautes saiu do módulo na versão 18.0.1.0.1: ficava
atrás do bloqueio, não era executado por nenhuma ação e já não rodava na
18.0 (usava o campo `cnpj_cpf` do contato, que deixou de existir). Para
consultar o leiaute antigo, veja o histórico do git do módulo (commit
`524f68b9`, que criou os geradores).

O que substitui este módulo no roteiro da folha é a conferência entre a
folha apurada no Odoo e o que os sistemas atuais mostram: FGTS Digital,
para o FGTS por competência, e DCTFWeb, para as contribuições
previdenciárias e o IRRF. Essa frente é tratada fora deste módulo, junto
do eSocial.
