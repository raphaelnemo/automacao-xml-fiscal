```markdown
# 🏛️ ERP Fiscal — Captação Passiva & Gestão de Documentos (NFS-e / NF-e)

Sistema ERP desenvolvido em Python para gestão fiscal contábil, focado no monitoramento, captura passiva em lote e controle auditável de notas fiscais eletrônicas de serviços (NFS-e) e produtos (NF-e).

## 🚀 Principais Funcionalidades

- **Captura Passiva & Consultas em Lote:** Módulo de varredura sequencial por NSU com suporte a múltiplos clientes selecionados simultaneamente e barra de progresso em tempo real.
- **Motor de Agendamento Automático (`agendador.py`):** Processamento em segundo plano com regras de espaçamento de requisições para evitar bloqueios na Sefaz/ADN Nacional.
- **Servidor Mock Sefaz/ADN Dinâmico (`mock_sefaz_server.py`):** API Flask simulada para testes completos de homologação com geração e resposta de payloads XML e JSON.
- **Repositório Fiscal Inteligente:** Interface compacta inspirada no padrão RM com seleção por linha, filtros dinâmicos por texto (Chave de Acesso, CNPJ ou Emitente) e suporte à paginação.
- **Exportação Flexível:** Geração instantânea de pacotes compactados (`.zip`) contendo arquivos XML e geração de relatórios tabulares resumidos em PDF via `ReportLab`.
- **Importador em Lote de Clientes:** Carga massiva via arquivo CSV com checagem de concorrência de NSU e validação de CNPJs.
- **Segurança & Auditoria:**
  - Hashing de senhas via `bcrypt` e política de expiração de credenciais.
  - Controle de acesso baseado em funções (*Role-Based Access Control* - Admin/Operador).
  - Trilha de auditoria abrangente (`auditoria_logs`) registrada no banco e em arquivos de log formatados em JSON.
  - Gerenciamento de certificados digitais A1/A3 via Windows Certificate Store (`LocalMachine` / `CurrentUser`).

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.11+
- **Frontend / Interface:** Streamlit
- **Banco de Dados:** SQLite3 (com `PRAGMA journal_mode=WAL` e controle de travamento de threads)
- **APIs & Backend:** Flask / Requests
- **Relatórios & Manipulação de Dados:** ReportLab, Pandas
- **Segurança:** Bcrypt

---

## 📁 Estrutura de Diretórios

```text
├── app/
│   └── app.py                  # Interface principal Streamlit e lógica do ERP
├── segredos/                   # Banco de dados local SQLite e configurações
├── logs/                       # Logs de auditoria do sistema em formato JSON
├── armazenamento/              # Repositório de arquivos temporários e notas
├── agendador.py                # Motor de agendamento em segundo plano
├── mock_sefaz_server.py        # Servidor Mock de testes da Sefaz/ADN
└── requirements.txt            # Dependências do projeto

```

---

## ⚙️ Instruções de Instalação e Execução

### 1. Clonar o repositório

```bash
git clone [https://github.com/SEU-USUARIO/NOME-DO-REPOSITORIO.git](https://github.com/SEU-USUARIO/NOME-DO-REPOSITORIO.git)
cd NOME-DO-REPOSITORIO

```

### 2. Configurar o ambiente virtual

```bash
python -m venv .venv
# No Windows PowerShell:
.\.venv\Scripts\activate

```

### 3. Instalar as dependências

```bash
pip install -r requirements.txt

```

### 4. Executar os módulos

* **Servidor Mock (para ambiente de testes):**
```bash
python mock_sefaz_server.py

```


* **Painel do ERP (Streamlit):**
```bash
streamlit run app/app.py

```


* **Agendador de Tarefas Automáticas:**
```bash
python agendador.py

```



---

## 🔒 Nota de Segurança

Este repositório foi configurado com um arquivo `.gitignore` rigoroso para garantir que nenhum banco de dados com dados de clientes, arquivos de certificado digital, credenciais de acesso ou logs de execução sejam versionados.

```