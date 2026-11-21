Technical module for the CI of this repository. It is not meant for production
databases.

The CI installs only the modules of this repository and their dependencies. Without
a Brazilian chart of accounts module, the demo companies of `l10n_br_base` have no
chart of accounts and any test that creates an invoice, a journal entry or a payslip posting on them fails. Depending on
`l10n_br_coa_generic` loads the Brazilian chart on the demo companies, as in the
OCA/l10n-brazil CI.
