# Palpite Milionário

Gerador de palpites para loterias brasileiras, em migração para Linux/WSL, com interface Tkinter e layout `src/`.

## Requisitos

- Python 3.12 ou superior e Tkinter da mesma instalação Python.
- Ambiente gráfico Linux ou WSL 2 com WSLg.
- Navegador padrão configurado para visualizar PDFs.

## Preparar o ambiente Linux

Execute no terminal Ubuntu/WSL. Reutilize o ambiente `.venv` Linux quando já existir; não use um ambiente virtual Windows.

```bash
cd /mnt/d/apps_linux/palpiteiro
python3 -m venv .venv
.venv/bin/python -m pip install -e . --group dev
```

A instalação requer pip com suporte a `--group` (25.1 ou superior). No Ubuntu, se necessário, instale os pacotes de sistema `python3-venv` e `python3-tk` compatíveis com seu Python. Para atualizar as dependências do ambiente existente, execute apenas o comando `pip install` acima.

## Executar em modo gráfico

```bash
cd /mnt/d/apps_linux/palpiteiro
.venv/bin/python -m palpiteiro
```

Também são aceitos `.venv/bin/python -m palpiteiro.main` e `.venv/bin/palpite-milionario`. Feche e reabra o aplicativo após alterar o código-fonte.

## Executar em modo linha de comando

```bash
.venv/bin/python -m palpiteiro --listar
.venv/bin/python -m palpiteiro mega-sena
.venv/bin/python -m palpiteiro lotofacil -n 3
.venv/bin/python -m palpiteiro --versao
```

## Testes

```bash
.venv/bin/python -m pytest
```

Os testes cobrem recuperação do cache, falhas de gravação, geração e conferência de PDFs e o fallback de maximização do histórico. A validação visual deve incluir abrir o histórico, rolar seu conteúdo e restaurar/redimensionar a janela.

## Compilação local Linux — Opção 1

No terminal Ubuntu/WSL, após instalar as dependências de desenvolvimento:

```bash
cd /mnt/d/apps_linux/palpiteiro
.venv/bin/python -m pytest
.venv/bin/python -m PyInstaller --clean --distpath app_compilado/2026.04.080 --workpath build/linux palpiteiro-linux.spec
./app_compilado/2026.04.080/palpite-milionario/palpite-milionario
```

O resultado é uma distribuição Linux x86_64 em diretório. Mantenha a pasta `_internal` junto do executável. Não precisa instalar o aplicativo nem ativar o ambiente virtual para executá-lo. Os dados continuam na pasta pessoal do usuário Linux. Para compilações futuras, use uma pasta de saída nova para preservar o artefato anterior. Esta distribuição deve ser validada em outras distribuições Linux antes de ser disponibilizada a terceiros.

## Release Flatpak — Opção 2

O manifesto está em `flatpak/io.github.surdo64.palpite-milionario.yml`. Com `flatpak` e `flatpak-builder` instalados, execute no Ubuntu/WSL:

```bash
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak-builder --user --install --force-clean build/flatpak flatpak/io.github.surdo64.palpite-milionario.yml
flatpak run io.github.surdo64.palpite-milionario
```

O manifesto usa somente os sockets gráficos necessários ao Tkinter. A submissão ao Flathub exige revisão posterior de licença, identidade, screenshots, metadados e dependências; esta Opção 2 local não publica externamente.

## Dados e recuperação

O cache fica em `$XDG_DATA_HOME/palpite-milionario/estatisticas.json` ou, na ausência da variável, em `~/.local/share/palpite-milionario/estatisticas.json`.

A gravação usa substituição atômica e preserva a versão anterior válida em `estatisticas.json.bak`. Um cache inválido é copiado para um arquivo exclusivo `estatisticas-recuperacao-*.json` antes de ser substituído. O aplicativo tenta recuperar o backup e informa o problema; se não puder preservar o original, bloqueia a gravação. As cópias de recuperação não são apagadas automaticamente.

## Visualização e impressão

**Visualizar palpites para impressão** gera diretamente um PDF A4 em uma pasta temporária exclusiva do usuário e solicita sua abertura no navegador. Salvar uma cópia e imprimir são ações manuais. Não há impressão automática.

No WSL, usa o navegador padrão do Windows, resolvido pela associação HTTPS. Uma cópia temporária com nome exclusivo é criada na pasta temporária do usuário Windows para permitir a visualização. É necessário manter a interoperabilidade do WSL habilitada. No Linux nativo, usa o navegador configurado no ambiente Linux. Nenhuma associação de arquivos ou navegador padrão é alterada pelo aplicativo.

O PDF contém os dados dos palpites para conferência posterior, inclusive quando copiado ou salvo pelo navegador. Use **Salvar/baixar** para preservar esses dados; imprimir novamente em PDF pode descartá-los. Os temporários permanecem disponíveis para a sessão do navegador e ficam sujeitos à limpeza de temporários do sistema.

**Salvar palpites** mantém a exportação TXT estruturada. Arquivos TXT e HTML antigos continuam aceitos na conferência. PDFs antigos continuam aceitos com seu TXT auxiliar ao lado.

Esta cópia Linux não usa MSIX nem Microsoft Store. O histórico da versão Windows é mantido no changelog; instruções de empacotamento Windows não se aplicam a este diretório.

## Conferência de palpites

Ao conferir um arquivo de palpites, o aplicativo compara os números com o resultado oficial e informa as faixas correspondentes para fins de consulta. O aplicativo não realiza apostas nem movimenta dinheiro. A classificação contempla trevos da +Milionária, os dois sorteios da Dupla Sena, Mês da Sorte, colunas do Super Sete e a premiação de zero acertos da Lotomania.

O valor do prêmio deve ser confirmado no resultado oficial da CAIXA, pois pode depender do rateio do concurso.

## Loterias suportadas

- Mega-Sena
- Lotofácil
- Quina
- +Milionária
- Lotomania
- Dupla Sena
- Dia de Sorte
- SuperSete
