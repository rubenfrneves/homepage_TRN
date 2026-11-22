# Backoffice TRN (ADMIN TIC)

Endereço: `https://rubenfrneves.github.io/homepage_TRN/admin/`. Utilizador: **ADMIN TIC**. Senha: a que definir no passo 1.

## Como funciona
- Edita todos os textos e dados (empresa, contactos, 3 idiomas) e substitui fotografias.
- "Publicar" grava as alterações no GitHub; uma tarefa automática refaz o site e atualiza-o em 2 a 3 minutos.
- Segurança: o site é estático, por isso o login é uma barreira de acesso à página. **A proteção real é o token do GitHub**: sem ele ninguém publica. A senha (código cifrado) fica num repositório público: use 12 ou mais caracteres, única.

## Instalação (uma só vez)
1. **Senha.** No Terminal, dentro da pasta `TRN-propostas-A-B_gerador`: `python3 gerar.py --senha`. Cria `content/admin.json`.
2. **Carregar no GitHub** (pelo Safari/Chrome): no repositório, *Add file → Upload files* e arraste a pasta `TRN-propostas-A-B_gerador` inteira.
3. **Tarefa automática:** *Add file → Create new file*, nome `.github/workflows/publicar.yml`, cole o conteúdo de `github-workflow/publicar.yml` e *Commit*.
4. **Pages:** *Settings → Pages → Source: GitHub Actions*. O endereço do site mantém-se.
5. **Token:** *GitHub → Settings → Developer settings → Fine-grained tokens*, só para este repositório, *Contents: Read and write* (e *Actions: Read-only*, opcional). Cole-o no primeiro acesso ao backoffice; fica cifrado no navegador.

## Notas
- Alterar a senha: separador Segurança.
- Perdeu a senha: volte a executar `gerar.py --senha` e carregue o `content/admin.json` novo.
- O site só tem a Opção A; a `index.html` da raiz reencaminha para ela no idioma do navegador.
- WhatsApp: enquanto `whatsapp` estiver vazio em *Dados da empresa*, os botões de WhatsApp não aparecem. Ao preencher (ex.: 351912345678) passam a aparecer.
- Vídeo promocional: `static/video/promo-trn.mp4` (secção "Conheça a TRN em vídeo").
- A tarefa automática não pôde ser testada fora do GitHub; se falhar, veja o separador *Actions* do repositório.
