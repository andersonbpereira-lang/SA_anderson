# HospitalCare — Sistema didático de gestão hospitalar

**Estudante:** Anderson Becker Pereira  
**Turma:** Técnico em Desenvolvimento de Sistemas — M1  
**Unidade curricular:** Programação de Aplicativos  
**Projeto:** HospitalCare

## Objetivo
Aplicação educacional para praticar cadastro de pacientes fictícios, registro de atendimentos simulados, organização de fila e persistência em SQLite.

> **Aviso:** este projeto é uma simulação acadêmica. A classificação de prioridade é uma regra didática, não é o Protocolo de Manchester nem protocolo clínico validado. Não realiza diagnóstico ou recomendação de tratamento e não deve orientar atendimento real. Use exclusivamente dados fictícios.

## Arquitetura integrada
- `codigo/app.py`: regras, validações, banco SQLite, testes e API Flask.
- `interface/index.html`: estrutura da interface.
- `interface/style.css`: aparência responsiva.
- `interface/script.js`: interações e chamadas à API; não armazena dados em localStorage.
- `banco_de_dados/hospital.db`: criado automaticamente na execução.

A interface e o menu de terminal utilizam as mesmas tabelas SQLite: `pacientes` e `atendimentos`.

## Requisitos
- Python 3.9 ou superior.
- Flask, instalado pelo requirements.txt.
- Navegador atualizado.

## Executar no Windows
Abra o terminal na pasta raiz do repositório:

```bash
python -m pip install -r requirements.txt
python codigo/app.py --web
```

Acesse http://127.0.0.1:5000

**Credenciais demonstrativas:** usuário `admin`, senha `hospital123`. O login é fixo e não é autenticação segura; não exponha o servidor na internet.

Para executar o menu de terminal:

```bash
python codigo/app.py
```

Os dois modos compartilham o mesmo banco.

## Funcionalidades
1. Cadastro e consulta de pacientes fictícios.
2. Cálculo demonstrativo de IMC.
3. Registro de queixa e informações simuladas.
4. Classificação didática em cinco níveis (azul, verde, amarelo, laranja e vermelho).
5. Fila ordenada pela prioridade calculada e horário.
6. Início e finalização de atendimentos.
7. Busca e exclusão com validação de atendimentos em andamento.
8. Limpeza dos registros fictícios pelo botão na interface.

## Testes
Na raiz:

```bash
python codigo/app.py --testes
```

Os testes cobrem cálculos, validações, cadastro, registro, ordenação da fila, atualização de status e exclusão em cascata.

## Limitações e privacidade
- Use somente dados inventados para fins escolares.
- O login demonstrativo não protege dados; não existe gestão real de usuários.
- Não utilize dados pessoais ou clínicos reais.
- SQLite local é adequado para desenvolvimento didático, não para operação hospitalar.
- A classificação não substitui avaliação profissional.
- Limpar os dados remove todos os registros deste banco.

## Estrutura
```text
.
├── README.md
├── requirements.txt
├── codigo/app.py
├── interface/
│   ├── index.html
│   ├── script.js
│   └── style.css
└── banco_de_dados/
    ├── estrutura.sql
    ├── crud.sql
    └── hospital.db (gerado automaticamente)
```
