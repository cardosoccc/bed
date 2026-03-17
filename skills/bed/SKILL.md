# bed

bed é uma ferramenta cli de gestão de portfólio pessoal. todos os dados ficam em um banco sqlite local em `~/.bed/bed.db`. comandos são executados via `bed` (ou `uv run bed` em desenvolvimento).

## regras fundamentais

- toda operação de gestão de ativos e regras opera sobre o portfólio local.
- sempre inicialize o banco primeiro: `bed portfolio init` (ou `bed p init`)
- ativos podem ser referenciados por UUID, índice numérico da lista (coluna `#`), ou nome.
- regras podem ser referenciadas por UUID ou índice numérico da lista.
- valores monetários usam decimais com duas casas (ex: 1500.00).
- proporções em regras são valores entre 0 e 1 (ex: 0.60 = 60%).

## sistema de aliases

bed usa aliases de uma letra para agilidade. sempre prefira aliases aos nomes completos.

### grupos de comandos

| alias | comando |
|-------|---------|
| `a` | asset (ativo) |
| `r` | rule (regra) |
| `p` | portfolio (portfólio) |
| `c` | config (configuração) |

### subcomandos

| alias | subcomando |
|-------|------------|
| `c` | create (criar) |
| `e` | edit (editar) |
| `d` | delete (excluir) |
| `l` | list (listar) |
| `s` | status (portfólio) / set (config) |

### atalhos de listagem

comandos de duas letras listam um recurso diretamente: `aa` (ativos), `rr` (regras), `pp` (status do portfólio).

## fluxo de configuração

execute estes comandos para configurar um novo ambiente bed:

```bash
bed p init
bed a c -n AAPL --class equity --type stock -q 10 -i 1500 -c 1700
bed r c --description "equity target" --class equity --proportion 0.60
```

## gerenciando ativos

```bash
# criar ativo
bed a c -n AAPL --class equity --type stock -q 10 -i 1500 -c 1700

# criar ativo com categoria e tags
bed a c -n VGLT --class fixed-income --type etf -q 50 -i 3000 -c 3200 --category bonds -t long-term

# listar ativos
bed aa

# editar ativo por nome
bed a e AAPL -c 1800

# editar ativo por índice
bed a e 3 -q 15

# excluir ativo
bed a d AAPL
```

### opções de criação/edição de ativos

| opção | alias | descrição |
|-------|-------|-----------|
| `--name` | `-n` | nome do ativo (obrigatório na criação) |
| `--description` | `-d` | descrição do ativo |
| `--class` | | classe: equity, fixed-income (obrigatório na criação) |
| `--type` | | tipo: stock, bond, fund, etf, reit, crypto, other (obrigatório na criação) |
| `--quantity` | `-q` | quantidade (padrão: 0) |
| `--initial-value` | `-i` | valor investido (padrão: 0) |
| `--current-value` | `-c` | valor atual (padrão: 0) |
| `--category` | | categoria |
| `--subcategory` | | subcategoria |
| `--tags` | `-t` | tags separadas por vírgula |

## gerenciando regras

```bash
# criar regra de alocação por classe
bed r c --description "equity allocation" --class equity --proportion 0.60

# criar regra com banda min/max (diff=0 quando dentro da banda)
bed r c --description "equity band" --class equity -p 0.60 --min-proportion 0.50 --max-proportion 0.70

# criar regra com filtro por categoria
bed r c --description "bonds target" --category bonds --proportion 0.30

# criar regra com filtro por tags
bed r c --description "long-term" -t long-term --proportion 0.50

# listar regras
bed rr

# editar regra por índice
bed r e 1 --proportion 0.65

# excluir regra
bed r d 2
```

### cálculo do diff no portfólio

ao exibir o status do portfólio, o diff de cada classe/tag é calculado:

1. **somente target** (proportion definido, sem min/max): `diff = atual - target`
2. **min e max** (banda definida): se atual está dentro da banda `[min, max]`, `diff = 0`. abaixo do min: `diff = atual - min`. acima do max: `diff = atual - max`.
3. **somente min**: `diff = 0` quando acima do min; `diff = atual - min` quando abaixo.
4. **somente max**: `diff = 0` quando abaixo do max; `diff = atual - max` quando acima.

## visualizando status do portfólio

```bash
# status do portfólio
bed p s

# atalho
bed pp
```

o relatório mostra:
1. **por classe** — distribuição entre equity e fixed-income com proporções atuais
2. **por tags** — agrupamento por tags com valores e proporções
3. **regras** — comparação entre proporção alvo e proporção atual de cada regra

## resolução de ids

bed aceita nomes legíveis em qualquer lugar onde UUIDs são esperados:
- ativos: `bed a e AAPL -c 1800` (resolve "AAPL" para UUID)
- índices: `bed a e 3 -c 1800` (resolve índice #3 da lista para UUID)
- regras: `bed r e 1 --proportion 0.70` (resolve índice #1 para UUID)

## sincronização com nuvem

```bash
# configurar aws
bed c aws
bed c s bucket s3://meu-bucket/bed

# configurar gcp
bed c gcp
bed c s bucket gs://meu-bucket/bed

# enviar banco local para nuvem
bed p push

# baixar mais recente da nuvem
bed p pull

# forçar push/pull (ignora verificação de versão)
bed p push --force
bed p pull --force
```

## gerenciamento do banco de dados

```bash
bed p init       # inicializar banco (seguro executar várias vezes)
bed p destroy    # excluir arquivo do banco (irreversível, pede confirmação)
```

## erros comuns e soluções

**"database not found"** — execute `bed p init` para inicializar o banco.

**"asset not found"** — verifique o nome ou índice com `bed aa`.

**"rule not found"** — verifique o índice com `bed rr`.

**proporção incorreta** — use valores entre 0 e 1 (ex: 0.60 para 60%), não percentuais inteiros.

## referências

- [README](references/README.md)
