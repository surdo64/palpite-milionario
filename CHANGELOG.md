# Changelog

## 2026.04.078 - 06/10/2026 - Linguagem recreativa e pacote Flatpak atualizado

- Esclarecido que o aplicativo gera combinações para estudo e entretenimento, sem realizar apostas ou movimentar dinheiro.
- Atualizados a interface, os relatórios, a documentação e os metadados Flatpak para refletir essa finalidade.
- Reconstruído o executável Linux e o bundle Flatpak após os ajustes.

## 2026.04.077 - 17/09/2026 - Interface multilíngue e acesso ao site de loterias

- Adicionado seletor com dez idiomas para a interface principal e textos operacionais.
- Mantidos os nomes oficiais das modalidades de loteria sem tradução.
- Adicionados logotipos uniformes, cartões alinhados e link clicável para o site de loterias da CAIXA.

## 2026.04.076 - 17/09/2026 - Remoção dos destaques da CAIXA

- Removidas da interface as ações “Copiar Palpite” e “Abrir Loterias CAIXA”, que dependiam do fluxo bloqueado pela CAIXA.
- Mantidas a geração, o salvamento, a conferência e a visualização para impressão dos palpites.

## 2026.04.075 - 17/09/2026 - Remoção da transferência para a CAIXA

- Removido o recurso de transferência e preenchimento assistido no portal da CAIXA, conforme decisão do usuário.
- Eliminadas as janelas de progresso e os comandos relacionados ao preenchimento de jogos no site externo.
- O aplicativo não automatiza login, marcação de dezenas, carrinho, confirmação ou pagamento.

Este histórico reúne as versões comprovadas pelos arquivos-fonte e pelos pacotes preservados do projeto. As versões intermediárias entre `1.0.0` e `2026.04.068` não possuem registros individuais disponíveis; por isso, suas melhorias acumuladas estão consolidadas na entrada da versão `2026.04.068`, sem atribuições ou datas presumidas.

## 1.0.0 - Lançamento inicial

**Data de lançamento:** 18/04/2026

- Disponibilizada a primeira versão do Palpite Milionário para geração de jogos de loterias brasileiras.
- Incluído o catálogo inicial com Mega-Sena, Lotofácil, Quina, +Milionária, Lotomania, Dupla Sena, Dia de Sorte e Super Sete.
- Implementadas a interface gráfica para Windows e a interface de linha de comando, permitindo escolher a modalidade, a quantidade de jogos e gerar palpites.
- Adotada a estrutura Python com layout `src/`, gerenciamento de dependências por `uv` e testes automatizados com `pytest`.
- Incluídas as configurações básicas de cada loteria, como quantidade de números, limites de seleção, identificação por aliases e valores oficiais das apostas.

## 2026.04.068 - Consolidação do ciclo inicial

**Data de lançamento:** 20/04/2026

- Consolidado o ciclo evolutivo iniciado após a versão `1.0.0`, reunindo em uma versão distribuível os recursos desenvolvidos nas versões intermediárias sem registros individuais preservados.
- Integrado o histórico oficial de concursos da Caixa, com armazenamento em cache local e cálculo de estatísticas para apoiar a geração dos palpites.
- Adicionados perfis estatísticos de geração, ponderação por frequência e recência, validação de combinações e estratégia de fechamento para criar lotes com menor repetição total.
- Implementada a visualização do histórico completo de resultados por modalidade, incluindo tratamentos específicos para Dupla Sena, +Milionária, Dia de Sorte e Super Sete.
- Criados relatórios em HTML e texto, com organização automática de colunas conforme a modalidade e a quantidade de dezenas, além de arquivos auxiliares para posterior conferência.
- Adicionada a conferência de jogos salvos com os resultados oficiais, contemplando as regras particulares de premiação e comparação de cada loteria suportada.
- Preparados o executável Windows, os recursos visuais do aplicativo e o empacotamento para a Microsoft Store nos formatos MSIX e MSIXUPLOAD.
- Ampliada a cobertura automatizada para catálogo de loterias, geração de jogos, leitura de resultados, estatísticas, exportação e conferência.

## 2026.04.069 - Atualização e histórico de resultados

**Data de lançamento:** 20/07/2026

- Corrigida a atualização do histórico exibido após uma sincronização manual, garantindo que janelas de histórico já abertas sejam redesenhadas com os dados mais recentes.
- Separados o processamento da atualização remota e a gravação do cache por modalidade, impedindo que uma falha isolada descarte resultados obtidos com sucesso para outras loterias.
- Adicionadas novas tentativas automáticas para falhas temporárias de comunicação com a API da Caixa, aumentando a confiabilidade da sincronização dos resultados oficiais.
- Preservados no cache os dados das modalidades atualizadas quando outra consulta falha durante a mesma execução.
- Melhoradas as mensagens da interface para apresentar o erro real da atualização, facilitando a identificação de indisponibilidade da API ou problemas de conexão.
- Adicionado reconhecimento de DPI por monitor (`PerMonitorV2`) para melhorar a nitidez e o comportamento da interface em telas de alta resolução e em mudanças entre monitores.
- Incluídos testes para repetição de requisições HTTP, atualização parcial por modalidade, compatibilidade com dados carregados do cache e redesenho de janelas de histórico abertas.

## 2026.04.070 - 18/08/2026 - Correção histórico de resultados

- Janela de histórico agora abre automaticamente na última página (último concurso), mantendo ordem crescente.

## 2026.04.071 - 18/08/2026 - Atualização automática e correção MSIX

- Corrigido argumento shell:AppsFolder injetado pelo shell MSIX ao abrir pelo atalho, que impedia a GUI de iniciar.
- Adicionada verificação silenciosa de atualizações via Microsoft Store ao iniciar como MSIX.

## 2026.04.072 - 16/09/2026 - Identificação de premiações

- A conferência agora informa de forma explícita se o usuário foi contemplado com alguma premiação ou se nenhum jogo foi premiado.
- Cada jogo exibe `PREMIADO` com a faixa correspondente ou `NÃO PREMIADO`, além do total de jogos contemplados.
- Implementadas as faixas específicas das oito modalidades, incluindo trevos, Mês da Sorte, colunas, os dois sorteios da Dupla Sena e a faixa de zero acertos da Lotomania.
- Jogos premiados permanecem visíveis nos detalhes mesmo quando a conferência contém mais de 30 palpites.
- Incluídos testes de resultados premiados, não premiados e faixas mínimas para todas as loterias suportadas.
- Corrigida a atualização pela Microsoft Store para considerar somente uma versão superior do pacote principal, ignorando pacotes opcionais e de recursos.
- A instalação de atualização agora depende de autorização do usuário; também foi incluída verificação manual com abertura da página de atualizações da Store como alternativa.
## 2026.04.073 - 16/09/2026 - Suporte completo ao preenchimento assistido

- Adicionado preenchimento assistido, com conferência visual, para Dupla Sena, Dia de Sorte e Super Sete.
- Mantidos login, CAPTCHA, carrinho, pagamento e demais confirmações sob controle exclusivo do usuário.
- Validações específicas impedem dezenas inválidas, duplicidades, meses incorretos e combinações incompatíveis com cada volante.
- Atualizada a interface para disponibilizar a preparação assistida em todas as modalidades atualmente cadastradas.
## 2026.04.074 - 17/09/2026 - Correção do atalho e da verificação da Store

- O atalho da Área de Trabalho passa a abrir a identidade instalada pela Microsoft Store.
- Execuções locais não exibem mais alerta incorreto de falha ao consultar atualizações da Store.
- A verificação continua programática quando o aplicativo é iniciado como pacote MSIX.

## 2026.04.078 - 06/10/2026 - Robustez da versão Linux/WSL

- Protegida a leitura de cache inválido, preservando o arquivo original e recuperando a cópia anterior válida quando disponível.
- Implementadas gravação atômica e cópia de segurança do cache, sem mudar a estrutura dos dados ou o carregamento dos resultados oficiais.
- A visualização para impressão agora gera PDF A4 temporário, paginado e com dados incorporados para conferência posterior.
- Mantida a leitura de exportações TXT/HTML e de PDFs antigos acompanhados do arquivo auxiliar.
- Adicionado o ponto de entrada `python -m palpiteiro` e atualizadas as instruções para Linux/WSL.
- Acrescentados testes de recuperação, falhas de gravação, PDF e maximização do histórico no Linux.
- Corrigida a largura dos cartões de loteria para exibir integralmente o rótulo “Dia de Sorte” em telas largas e diferentes escalas.
- Ajustada a fonte dos cartões para caber junto do indicador e do logotipo, mantendo os cartões em 190 px e evitando ultrapassagem da janela.

O histórico anterior foi preservado na ordem em que estava disponível; esta entrada registra as alterações da cópia Linux.
