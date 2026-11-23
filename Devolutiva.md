
# Devolutiva formativa — Atividade 02 da SA

**Estudante:** Anderson Becker Pereira  
**Turma:** São Bento do Sul — Manhã  
**Unidade Curricular:** Programação de Aplicativos  
**Projeto:** Hospital — HospitalCare  
**Repositório:** https://github.com/andersonbpereira-lang/SA_anderson  
**Arquivos observados:** `codigo/app.py`, `interface/index.html`, `interface/script.js` e `interface/style.css`  
**Data da verificação:** 23/11/2026  
**Escopo:** evidências técnicas dos critérios CT6 e CT7, sem atribuição de nota numérica.

## Situação atual do projeto

O repositório apresenta uma solução Python extensa para cadastro, atendimento e organização de filas, além de uma interface web interativa. O Python trabalha com SQLite e possui testes por linha de comando; a interface atual usa JavaScript e `localStorage`. Há evidências de duas partes desenvolvidas, mas a integração entre elas não está demonstrada no código publicado.

## Pontos positivos identificados

- Separou HTML, CSS e JavaScript em arquivos próprios e utilizou funções para as ações do usuário.
- Implementou telas de login demonstrativo, cadastro e consulta de pacientes, triagem e fila de atendimento.
- Incluiu validações de entradas e atualização dinâmica das tabelas e indicadores no navegador.
- No Python, organizou funções de cadastro, histórico, alteração de situações e cálculo de IMC.
- Adotou SQLite, tratamento de dados e uma rotina de testes acessível por `python app.py --testes`.

## O que precisa ser corrigido ou concluído

### 1. Unificar as duas implementações

A página web grava pacientes e atendimentos no `localStorage`, enquanto `codigo/app.py` mantém outros registros em SQLite e funciona pelo terminal. Essas bases não se comunicam. **Como melhorar:** escolher uma fonte de dados e documentar a integração futura. Nesta etapa, a interface pode ser demonstrada como protótipo independente, mas isso deve ser informado claramente.

### 2. Tratar o login como demonstração

As credenciais de acesso estão fixas no JavaScript; isso não é autenticação segura. **Como melhorar:** identificar o login como simulação, trabalhar apenas com dados fictícios e deixar uma futura autenticação real para o servidor.

### 3. Não apresentar uma triagem didática como decisão clínica

A classificação de prioridade é construída por regras do próprio programa e pode parecer um protocolo de saúde real. **Como melhorar:** identificar visivelmente a triagem como *simulação educacional*, não apropriada para decidir atendimento de pacientes reais.

### 4. Rever o tratamento de informações pessoais

Informações clínicas armazenadas no navegador podem ficar acessíveis no dispositivo. **Como melhorar:** usar registros fictícios, indicar a limitação do `localStorage` e testar a limpeza de dados de demonstração.

## Oportunidades de melhoria

- Atualizar o README com instruções distintas para executar o menu Python e abrir a interface web.
- Explicar quais regras estão implementadas em cada versão e padronizar nomes de campos e estados.
- Manter comentários úteis, evitando repetir em excesso o que já está claro nos nomes das funções.

## Testes recomendados

1. Cadastrar paciente fictício e verificar sua aparição na lista.
2. Tentar registrar idade, peso, altura ou sinais vitais inválidos.
3. Criar atendimento, alterar a situação e conferir a fila de prioridade.
4. Recarregar a página e conferir a persistência apenas no mesmo navegador.
5. Executar os testes do programa Python e comparar as regras com as da interface.
6. Confirmar que a classificação aparece identificada como demonstração.

## Prioridades para a próxima versão

1. **Documentar que web e Python são implementações ainda não integradas.**
2. **Padronizar as regras e identificar a triagem como simulação.**
3. **Utilizar exclusivamente dados fictícios no protótipo.**
4. **Ampliar testes de validação e registrar resultados.**

## Mensagem final

Anderson, a implementação revela boa iniciativa na organização dos recursos e no desenvolvimento de diferentes operações. Seu principal desafio agora é tornar clara a relação entre o sistema Python e a interface web, mantendo as validações e as informações consistentes.

---

**Registro da avaliação:** análise do conteúdo publicado no GitHub. Não foram executados testes completos de interface e integração no ambiente do estudante. Os critérios socioemocionais (CS1, CS2 e CS3) dependem da observação docente presencial. Arquivos vazios ou ausentes significam **sem evidência verificável no repositório**, e não nota zero automática.
