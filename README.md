# Telegram Manga Downloader

Script em Python para baixar automaticamente mangás de grupos ou canais do Telegram.

Os arquivos são organizados em pastas pelo nome da obra e podem ser baixados primeiro para o SSD e depois copiados para um cartão de memória ou outro disco.

## Funcionalidades

- Download automático de arquivos do Telegram
- Suporte a:
  - EPUB
  - MOBI
  - PDF
  - CBZ
  - CBR
  - ZIP
- Criação automática de pastas por mangá
- Verificação de arquivos já baixados
- Download de múltiplos arquivos simultaneamente
- Download temporário no SSD
- Cópia automática para cartão de memória
- Controle de espaço livre no SSD e no cartão
- Exibição da velocidade total dos downloads
- Arquivos já concluídos não são baixados novamente

## Exemplo de organização

```text
Mangas/
├── Berserk/
│   ├── Berserk Vol. 01.epub
│   └── Berserk Vol. 02.epub
│
├── JoJo's Bizarre Adventure/
│   ├── JoJo's Bizarre Adventure Vol. 01.epub
│   └── JoJo's Bizarre Adventure Vol. 02.epub
│
└── Undead Unluck/
    ├── Undead Unluck Vol. 01.epub
    └── Undead Unluck Vol. 02.epub
```

## Requisitos

- Python 3
- Telethon
- cryptg

Instale as dependências com:

```bash
pip install telethon cryptg
```

## Configuração

Crie uma aplicação em:

`https://my.telegram.org`

Pegue seu:

- `API_ID`
- `API_HASH`

Depois configure no script:

```python
API_ID = 12345678
API_HASH = "SEU_API_HASH"

GROUP = "@nome_do_grupo"

TEMP_DIR = Path(
    r"C:\Users\usuario\Downloads\telegram_mangas_temp"
)

DOWNLOAD_DIR = Path(
    r"F:\Mangas"
)
```

Também é possível alterar a quantidade de downloads simultâneos:

```python
MAX_DOWNLOADS = 4
```

## Executando

```bash
python script_mangas.py
```

Na primeira execução, o Telegram solicitará:

- número de telefone
- código de autenticação
- senha de verificação em duas etapas, caso esteja ativada

Depois disso, uma sessão local será criada e normalmente não será necessário fazer login novamente.

## Como funciona

```text
Telegram
   ↓
downloads simultâneos
   ↓
SSD temporário
   ↓
fila de cópia
   ↓
cartão de memória
```

Enquanto novos arquivos são baixados para o SSD, arquivos já concluídos podem ser copiados para o cartão de memória em paralelo.

Após confirmar que a cópia foi concluída corretamente, o arquivo temporário é removido do SSD.

## Segurança

Não publique suas credenciais do Telegram nem os arquivos de sessão.

Adicione ao `.gitignore`:

```gitignore
*.session
*.session-journal
```

## Observação

O script deve ser utilizado apenas em grupos ou canais aos quais sua conta do Telegram possui acesso.
