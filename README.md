# CP5 — Vinheria Agnello | IoT Full + Dashboard

> Solução IoT completa com ESP32, FIWARE e Dashboard Python para monitoramento ambiental da Vinheria Agnello — CP5 FIAP 2026

## Integrantes

| Nome | RM |
|------|----|
| João Victor Melo | 566640 |
| Gustavo Macedo | 567594 |
| Gustavo Hiruo | 567625 |
| Yan Lucas | 567046 |

**Turma:** 1ESPA
**Professor:** Fábio Henrique Cabrini
**Instituição:** FIAP — 2026

---

## Sobre o Projeto

Evolução do CP4, esta solução adiciona monitoramento de **temperatura** e **umidade** (sensor DHT22) à medição de luminosidade já existente, e transfere toda a **lógica de decisão** do hardware (ESP32) para um **dashboard Python** rodando como serviço Linux na nuvem.

O ESP32 agora atua apenas como ponto de coleta e atuação: publica os dados via MQTT no FIWARE e obedece comandos vindos do dashboard para acionar LED e buzzer quando há anomalias.

### Mudança de paradigma — do CP4 para o CP5

| | CP4 (Edge Computing) | CP5 (Fog/Cloud Computing) |
|---|---|---|
| Onde fica a lógica | No ESP32 | No dashboard Python (VM Azure) |
| Decisão de alerta | Hardware decide localmente | Software analisa e comanda hardware |
| Sensores | LDR | LDR + DHT22 (temperatura e umidade) |
| Atuadores | LED onboard | LED onboard + Buzzer |
| Visualização | Postman / STH-Comet | Dashboard web em tempo real |

---

## Arquitetura

```
┌─────────────────────┐        MQTT          ┌──────────────────┐
│  ESP32 + DHT22 +    │ ───────────────────▶│   Mosquitto      │
│  LDR + LED + Buzzer │   publica sensores   │   (broker MQTT)  │
└─────────────────────┘                      └────────┬─────────┘
         ▲                                            │
         │ comandos                                   ▼
         │ on/off                              ┌──────────────────┐
         │                                     │  IoT Agent MQTT  │
         │                                     │   (porta 4041)   │
         │                                     └────────┬─────────┘
         │                                              │
         │                                              ▼
         │                                     ┌──────────────────┐
         │                                     │ Orion Context    │
         │                                     │ Broker (1026)    │
         │                                     └────────┬─────────┘
         │                                              │
         │                                              ▼
         │                                     ┌──────────────────┐
         │                                     │   STH-Comet      │
         │                                     │   (porta 8666)   │
         │                                     └────────┬─────────┘
         │                                              │
         │                                              ▼
         │                                     ┌──────────────────┐
         │     publica via MQTT direto        │     MongoDB      │
         └─────────────────────────────────────│  (histórico)     │
                                               └──────────────────┘
                                                        ▲
                                                        │ HTTP GET
                                                        │
                                              ┌─────────┴─────────┐
                                              │ Dashboard Python  │
                                              │  (porta 5000)     │
                                              │  serviço Linux    │
                                              └───────────────────┘
```

Toda a infraestrutura FIWARE roda em **containers Docker** numa VM Ubuntu 24 hospedada no **Microsoft Azure** (`20.124.178.183`).

---

## Componentes da Solução

### Hardware (Wokwi)

| Componente | Pino ESP32 | Função |
|-----------|-----------|--------|
| Sensor LDR | GPIO 34 | Mede luminosidade |
| DHT22 | GPIO 4 | Mede temperatura e umidade |
| LED Azul | GPIO 2 | Alerta visual de anomalia (pisca) |
| Buzzer | GPIO 18 | Alerta sonoro de anomalia (1.5 kHz contínuo) |

### FIWARE (Docker na VM Azure)

| Componente | Função | Porta |
|-----------|--------|-------|
| Orion Context Broker | Gerenciamento de entidades e dados contextuais | 1026 |
| IoT Agent MQTT | Integração dos dispositivos IoT via MQTT | 4041 |
| STH-Comet | Armazenamento histórico de dados (time series) | 8666 |
| Eclipse Mosquitto | Broker MQTT | 1883 |
| MongoDB | Banco de dados NoSQL | 27017 |

### Dashboard

| Característica | Detalhe |
|---------------|---------|
| Linguagem | Python 3 |
| Framework | Dash (Plotly) + Flask |
| Porta | 5000 |
| Hospedagem | VM Azure (mesmo servidor do FIWARE) |
| Execução | Serviço Linux gerenciado por systemd |
| Atualização | Automática a cada 5 segundos |

---

## Entidade FIWARE

| Campo | Valor |
|-------|-------|
| Entity ID | `urn:ngsi-ld:Vinheria:001` |
| Entity Type | `SensorLDR` |
| Device ID | `vinheria001` |

### Tópicos MQTT

| Tópico | Direção | Conteúdo |
|--------|---------|----------|
| `/TEF/vinheria001/cmd` | Dashboard → ESP32 | Comandos `on` e `off` |
| `/TEF/vinheria001/attrs` | ESP32 → FIWARE | Estado geral do dispositivo |
| `/TEF/vinheria001/attrs/l` | ESP32 → FIWARE | Luminosidade (0–100%) |
| `/TEF/vinheria001/attrs/t` | ESP32 → FIWARE | Temperatura (°C) |
| `/TEF/vinheria001/attrs/h` | ESP32 → FIWARE | Umidade (%) |

---

## Lógica de Decisão (Thresholds)

A análise dos valores e a tomada de decisão acontece **integralmente no dashboard Python**, não mais no ESP32:

| Sensor | Limite mínimo | Limite máximo |
|--------|--------------|---------------|
| Luminosidade | 0% | 30% |
| Temperatura | 10°C | 15°C |
| Umidade | 50% | 70% |

Quando qualquer valor está fora do limite, o dashboard publica `vinheria001@on|` no broker MQTT e o ESP32 aciona LED + buzzer. Quando todos os valores voltam ao normal, o dashboard publica `vinheria001@off|` e o ESP32 desativa os alertas.

---

## Simulação no Wokwi

🔗 [Acesse a simulação completa do projeto no Wokwi](https://wokwi.com/projects/459869980812560385)

---

## Vídeo Demonstrativo

🎬 [Assista à demonstração completa no YouTube](#)

---

## Como Executar

### Pré-requisitos

- VM Ubuntu Server 24 com [FIWARE Descomplicado](https://github.com/fabiocabrini/fiware) instalado
- Portas liberadas no firewall: `1026`, `1883`, `4041`, `8666`, `5000`
- Python 3.10+ instalado
- Arduino IDE com bibliotecas `WiFi.h`, `PubSubClient` e `DHT sensor library`
- Postman com a collection do FIWARE Descomplicado importada

### Hardware (ESP32)

1. Abra o arquivo `vinheria_agnello_cp5.ino` na Arduino IDE ou no Wokwi
2. Ajuste o `SSID`, `PASSWORD` e o IP do broker MQTT conforme seu ambiente
3. Faça o upload para o ESP32 (ou rode a simulação no Wokwi)

### FIWARE (na VM)

```bash
# Conecta na VM
ssh -i "sua_chave.pem" azureuser@SEU_IP

# Sobe os containers
cd ~/fiware && sudo docker-compose up -d

# Verifica que tudo subiu
sudo docker ps
```

### Dashboard Python (na VM)

#### 1. Instalação

```bash
# Cria pasta e entra
mkdir ~/dashboard && cd ~/dashboard

# Copia os arquivos dashboard.py e requirements.txt para esta pasta

# Instala as dependências
pip install -r requirements.txt --break-system-packages
pip install paho-mqtt --break-system-packages
```

#### 2. Configuração como serviço Linux

Crie o arquivo `/etc/systemd/system/vinheria-dashboard.service` com o conteúdo do arquivo `vinheria-dashboard.service` deste repositório:

```bash
sudo nano /etc/systemd/system/vinheria-dashboard.service
```

Ative e inicie o serviço:

```bash
sudo systemctl daemon-reload
sudo systemctl enable vinheria-dashboard
sudo systemctl start vinheria-dashboard

# Verifica que está rodando
sudo systemctl status vinheria-dashboard
```

#### 3. Provisionamento no FIWARE (Postman)

No Postman, com a collection FIWARE Descomplicado importada, execute na ordem:

1. **IoT Agent MQTT → Provisioning a Service Group**
2. **IoT Agent MQTT → Provisioning a Smart Lamp**
3. **IoT Agent MQTT → Registering Smart Lamp Commands**
4. **STH-Comet → Subscribe Luminosity**
5. **STH-Comet → Subscribe Temperature**
6. **STH-Comet → Subscribe Humidity**

#### 4. Acesso

Abra no navegador: `http://SEU_IP:5000`

---

## Análise Histórica Complementar (Google Colab)

Como complemento à entrega principal, o repositório inclui um **notebook Google Colab** (`dashboard_colab.ipynb`) com gráficos Matplotlib que consomem a mesma API do STH-Comet, com auto-refresh a cada 5 segundos. É útil para análises pontuais e geração de relatórios estatísticos.

**Observação:** o Colab é um complemento — não substitui o dashboard web, que é a entrega oficial do CP5 conforme requisitos do enunciado (serviço Linux + porta 5000 + API).

---

## Estrutura do Repositório

```
cp5-vinheria-agnello/
├── README.md                          → este arquivo
├── hardware/
│   ├── vinheria_agnello_cp5.ino       → código do ESP32
│   └── diagram.json                    → circuito do Wokwi
├── dashboard/
│   ├── dashboard.py                    → dashboard web (entrega principal)
│   ├── requirements.txt                → dependências Python
│   └── vinheria-dashboard.service      → arquivo systemd
├── colab/
│   └── dashboard_colab.ipynb           → análise complementar no Google Colab
├── postman/
│   └── FIWARE_Descomplicado_CP5.json   → collection do Postman
└── images/                             → screenshots para documentação
    ├── arquitetura.png
    ├── dashboard.png
    ├── wokwi-circuito.png
    └── ...
```

---

## Referências

- [FIWARE Descomplicado — Prof. Fábio Cabrini](https://github.com/fabiocabrini/fiware)
- [Documentação do Orion Context Broker](https://fiware-orion.readthedocs.io/en/3.10.1/index.html)
- [Documentação do STH-Comet](https://fiware-sth-comet.readthedocs.io/en/latest/)
- [Documentação do IoT Agent MQTT](https://github.com/FIWARE/tutorials.IoT-Agent)
- [Dash by Plotly — Documentação](https://dash.plotly.com/)
- [Smart Data Models — FIWARE](https://github.com/smart-data-models)
