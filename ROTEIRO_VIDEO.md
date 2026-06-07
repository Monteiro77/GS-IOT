# 🎬 Roteiro do vídeo — Voxel Inspector

**Duração alvo:** 4 a 5 minutos · **Integrantes:** Vinicius Monteiro Araújo (RM 555088) e Guilherme Oliveira (RM 555180)

> O vídeo vale **50 pontos**. Os critérios são: explicar o problema/proposta, demonstrar o sistema
> funcionando, clareza da explicação, funcionamento da inferência visual e **estabilidade em
> diferentes condições (luz, movimento, distância)**. Este roteiro cobre todos eles.

---

## ✅ Antes de gravar (checklist)

- [ ] Ative o ambiente: `.\.venv\Scripts\Activate.ps1`
- [ ] Gere os vídeos de demo: `python samples/make_sample.py`
- [ ] Teste rápido: `python main.py --source samples/peca_ok.mp4` e `...peca_defeito.mp4`
- [ ] Tenha uma **peça impressa em 3D** (ou qualquer objeto retangular claro) sobre um fundo contrastante para a parte da webcam
- [ ] Deixe duas abas/janelas prontas: o **código no VSCode** e o **terminal**
- [ ] Grave em local bem iluminado; tenha uma lâmpada ou abajur por perto para a cena de "variação de luz"
- [ ] Áudio limpo (sem eco). Fale com calma.

---

## 🗣️ Roteiro (com falas e o que mostrar)

### 1. Abertura — *(0:00 – 0:25)* · **Vinicius**
> **Mostrar:** rostos / slide de título com nome do projeto e tema.

**Vinicius:**
> "Olá! Somos o Vinicius e o Guilherme. Nesse projeto da Global Solution, com o tema
> *Space Connect*, desenvolvemos o **Voxel Inspector** — uma solução de **Visão Computacional**
> que valida, em tempo real, peças impressas em 3D para uso no espaço."

---

### 2. O problema — *(0:25 – 1:10)* · **Guilherme**
> **Mostrar:** uma imagem de peça otimizada / satélite, ou slide com os números. Pode ser só você falando.

**Guilherme:**
> "Nosso projeto principal, o Voxel, gera as estruturas mais **leves** possíveis para o espaço,
> porque cada quilograma lançado em órbita custa entre **2.700 e 6.000 dólares**.
> Mas de nada adianta a geometria perfeita se a peça impressa sair com **defeito**.
> A impressão 3D sofre com falhas como **warping** — o empenamento por contração térmica —,
> **camadas mal fundidas** e **falhas de extrusão**. No espaço, uma peça estrutural com defeito
> pode comprometer uma missão de bilhões. Então surgiu a pergunta: *como validar visualmente
> cada peça, de forma automática, antes dela ser usada?*"

---

### 3. A proposta — *(1:10 – 1:55)* · **Vinicius**
> **Mostrar:** o terminal com o comando, prestes a rodar. Ou um diagrama simples do pipeline.

**Vinicius:**
> "A resposta é o Voxel Inspector. Ele usa uma **webcam comum** apontada para a peça e roda um
> **pipeline de OpenCV** em tempo real. O sistema **segmenta a silhueta** da peça com detecção
> de bordas Canny, mede a **planicidade da base** para identificar warping, analisa a
> **regularidade das camadas** com gradiente vertical, avalia a **solidez do contorno** para
> achar material faltando, e mede as **dimensões**. No fim, ele cruza tudo num **veredito**:
> aprovado, atenção ou defeito, com uma nota de 0 a 100."

---

### 4. Demonstração — *(1:55 – 3:50)* · **os dois**

#### 4a. Peça aprovada — **Vinicius**
> **Mostrar:** rodar `python main.py --source samples/peca_ok.mp4`

**Vinicius:**
> "Começando com uma peça **sem defeitos**. Repare no painel à direita: o contorno está verde,
> a base está plana, as camadas aparecem uniformes — todas as métricas em verde — e o veredito
> é **OK, nota 100**."

#### 4b. Peça com defeito — **Guilherme**
> **Mostrar:** rodar `python main.py --source samples/peca_defeito.mp4`

**Guilherme:**
> "Agora uma peça **defeituosa**. O sistema imediatamente acusa **DEFEITO**. A *planicidade da
> base* ficou vermelha — ele detectou o **warping**, a base empenada. A *solidez* caiu — tem
> **material faltando** na lateral, aquela mordida no contorno. E o espaçamento das **camadas**
> ficou irregular. A nota despencou."

#### 4c. Webcam ao vivo + estabilidade — **Vinicius e Guilherme**
> **Mostrar:** rodar `python main.py` (webcam) com uma peça real/objeto na mão.

**Vinicius:**
> "E funciona ao vivo. Aqui está a peça pela webcam, sendo analisada quadro a quadro."

> **Fazer na frente da câmera, falando o que está testando:**
> - **Distância:** aproxime e afaste a peça → "mesmo mudando a distância, ele continua segmentando."
> - **Movimento:** mexa/gire levemente a peça → "ele acompanha o movimento."
> - **Luz:** acenda/apague uma lâmpada ou cubra parte da luz → "e o pré-processamento com CLAHE
>   mantém a detecção estável mesmo variando a iluminação."

**Guilherme:**
> "Dá ainda pra ver o que o sistema enxerga: apertando **E**, mostramos o mapa de bordas do Canny;
> e com **C** calibramos a referência dimensional pra medir a peça em milímetros."
> **(apertar E e C ao falar)**

---

### 5. Código e repositório — *(3:50 – 4:30)* · **Guilherme**
> **Mostrar:** o VSCode com a pasta `voxel_inspector/` aberta, passando rápido por `analysis.py` e `inspector.py`.

**Guilherme:**
> "Sobre o código: ele é todo em **Python**, organizado em um pacote. O `analysis.py` tem as
> funções de visão computacional; o `inspector.py` junta as métricas no veredito; o `overlay.py`
> desenha o painel; e o `main.py` faz a captura em tempo real. Usamos **OpenCV** e **NumPy**.
> Tem até um gerador de peças sintéticas e um teste automático. Tudo está no **repositório
> público no GitHub**, com README e instruções."

---

### 6. Fechamento — *(4:30 – 4:55)* · **Vinicius**
> **Mostrar:** slide final / rostos.

**Vinicius:**
> "Resumindo: o Voxel Inspector garante que as peças mais leves do Voxel sejam também
> **confiáveis** — uma ponte entre a Terra e o espaço, que vale tanto para um satélite quanto
> para uma prótese ou um drone aqui embaixo. Obrigado!"

---

## 🎯 Dicas finais

- **Não leia travado:** use as falas como guia, fale natural.
- **Mostre a tela grande:** o painel de métricas precisa estar legível no vídeo.
- A parte **4c (webcam variando luz/movimento/distância)** é a que mais pontua em "estabilidade" — capriche nela.
- Se a webcam não pegar bem uma peça real, **não tem problema**: a demonstração com os vídeos
  `peca_ok.mp4` e `peca_defeito.mp4` já comprova a inferência visual funcionando.
- Suba no **YouTube como "não listado"** e coloque o link na entrega.
