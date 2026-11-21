Multiplicador de horas extras por faixa.

As faixas de multiplicador definem, por dia da semana e para feriados, a partir de quantas horas
e até quantas horas extras vale cada multiplicador. Quando o Odoo calcula as horas extras de uma
presença, as horas são distribuídas pelas faixas do dia e cada parte é multiplicada pelo fator da
sua faixa; o registro guarda as horas sem multiplicador, o multiplicador aplicado e a faixa.

O módulo também traz:

- exceções de presença, para que um dia seja tratado como outro dia da semana (por exemplo, um
  sábado trabalhado como dia útil);
- um assistente para registrar o pagamento de horas extras, que baixa o valor pago do saldo do
  funcionário.

Os feriados vêm do `l10n_br_hr_holidays_public`.
