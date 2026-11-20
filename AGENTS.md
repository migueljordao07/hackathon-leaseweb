# AGENTS.md

Instruções para assistentes de IA (Claude, ChatGPT/Codex, Gemini) que trabalham neste repositório.

## Contexto obrigatório

Antes de qualquer tarefa, ler os ficheiros em `00_Contexto/`:

| Ficheiro | Conteúdo |
|----------|----------|
| [00_Contexto/challenge-and-guidelines.md](00_Contexto/challenge-and-guidelines.md) | Desafio, temas, regras, critérios de avaliação e horário (transcrição do PDF oficial) |
| [00_Contexto/equipa.md](00_Contexto/equipa.md) | Membros, ferramentas de IA disponíveis e regras de colaboração |
| `00_Contexto/Hackathon Portugal 2026 - Challenge & guidelines overview 1 Finalito.pdf` | PDF original da organização |

## Resumo do projeto

- Hackathon Portugal 2026 — InfraHack: AI for Cloud Infrastructure (Leaseweb × Velv), 20 nov 2026, Lisboa.
- Equipa de 5: Miguel, Francisco, Carolina, Diogo, Ricardo.
- Começa do zero no dia; desenvolvimento das 08:45 às 15:45; pitch de 5 minutos no máximo.

## Regras para os agentes

- O `README.md` na raiz é o README do projeto entregue ao júri: em inglês, conciso, com objetivo, estrutura e instruções de build/run. Não o usar para notas internas.
- O repositório é público: nunca escrever segredos (chaves de API, passwords, credenciais da VM) em ficheiros versionados. Usar `.env` local, listado no `.gitignore`.
- Preferir linguagens comuns (Python, Go, PHP) e dependências open-source publicamente disponíveis, sempre declaradas nas instruções de build.
- O projeto tem de ter licença aberta que permita reutilização comercial e não comercial (ex.: Apache-2.0).
- O código tem de correr numa VM Linux (a fornecida pela organização) e a demo ao vivo conta para a avaliação: privilegiar algo que funcione de forma fiável.
- Commits pequenos e frequentes; a equipa trabalha em paralelo no mesmo repositório.
- Ao acrescentar novo contexto, criar um `.md` em `00_Contexto/` e atualizar a tabela acima.
