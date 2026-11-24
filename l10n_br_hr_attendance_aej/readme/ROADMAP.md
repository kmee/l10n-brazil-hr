- **Atributos CAdES da assinatura do AEJ.** O art. 88, par. 2, da Portaria MTP
  671/2021 pede o AEJ assinado no padrão CAdES, em `.p7s` destacado. O módulo
  gera um CMS destacado (SHA-256, com o certificado do signatário e a cadeia)
  pela `cryptography`, que grava os atributos assinados `contentType`,
  `messageDigest`, `signingTime` e `smimeCapabilities`. Ainda faltam o
  atributo `signing-certificate-v2` (RFC 5035), que o CAdES-BES exige, e o
  identificador de política de assinatura da ICP-Brasil (DOC-ICP-15.03), que
  a `cryptography` não gera. A assinatura confere com `openssl cms -verify`,
  mas um validador CAdES estrito pode recusá-la até esses atributos entrarem.
