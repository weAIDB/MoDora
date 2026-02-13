# MoDora


## ✨ Introduction

MoDora is an LLM-powered framework for semi-structured document analysis. It introduces the Component-Correlation Tree (CCTree) to model semi-structured documents with diverse elements and complicated layouts.

MoDora combines OCR, Embedding models and MLLMs in preprocessing, tree construction and tree-based analysis, without the need for extra training or fine-tuning. The experiment on two datasets with various documents and question types demonstrates its superior performance compared to existing methods.

**Examples**
| **Question**                                                                                                                       | **Answer**                                   | **UDOP**                                                                                  | **DocOwl2**                                                                  | **M3DocRAG**                                                         | **SV-RAG**                                                                                                        | **TextRAG**                                                                                                  | **ZenDB**                                                                  | **QUEST**                                   | **GPT-5**                                      | **MoDora **                                                                    |
|------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------|-------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|----------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|---------------------------------------------|------------------------------------------------|--------------------------------------------------------------------------------|
| Is Bitmex launched earlier than South Korea's ban on Bitcoin derivatives?                                                          | Yes                                          | no                                                                                        | Yes                                                                          | Yes                                                                  | Yes, Bitmex was launched in 2014, while South Korea's ban on Bitcoin derivatives was announced in 2017.           | Yes. BitMEX launched in 2014, while South Korea’s Bitcoin derivatives ban began on 2017-12-11.               | Not specified.                                                             |                                             | Yes.                                           | Yes—BitMEX launched in Jan 2014, while South Korea’s ban was on Dec 11, 2017.  |
| What is the title at the top of the third page?                                                                                    | Preface                                      | The title of the third page is "The Changing World"                                       | PREFACE                                                                      | 2018 Global Digital Asset Derivatives Research Report                | 2018 Global Digital Asset Derivatives Research Report                                                             | LEGAL NOTICES                                                                                                | Digital Asset Derivatives                                                  | Not found.                                  | Working with Apps                              | PREFACE                                                                        |
| When was this document published?                                                                                                  | November 30, 2023                            | 2023 September 6, 2000                                                                    | 2023-11-10                                                                   | 2023-11-13                                                           | The document was published on November 30, 2023.                                                                  | The publication date is not stated in the provided text.                                                     | November 30, 2023                                                          | 2023-11-30                                  | November 30, 2023                              | November 30, 2023                                                              |
| What image is in the center of page 2?                                                                                             | QR code                                      | The image is in the center of page 2.                                                     | not answerable                                                               | A QR code.                                                           | QR code                                                                                                           | Not specified in the provided information.                                                                   | Not specified.                                                             | Not specified.                              | A QR code.                                     | A QR code.                                                                     |
| What was the decline in the electrical equipment industry last week?                                                               | 2.36%                                        | 3%                                                                                        | not answerable                                                               | -2.36%                                                               | The decline in the electrical equipment industry last week was 0.6%.                                              | Down 2.36%.                                                                                                  | Not specified in the provided context.                                     | -2.36%                                      | -3.4%                                          | Down 2.36%.                                                                    |
| What is the fourth section of the report?                                                                                          | Investment Strategy and Key Recommendations  | scientific report                                                                         | not answerable                                                               | Risk warning                                                         | The fourth section of the report is titled "2.2.1 New Energy Source."                                             | Not specified in the provided information.                                                                   | Investment Strategy and Key Recommendations                                | Unknown                                     | Real estate market                             | Investment Strategy and Key Recommendations                                    |
| How many references are there?                                                                                                     | 13                                           | 3                                                                                         | 37                                                                           | 13                                                                   | There are 5 references in the text.                                                                               | 11                                                                                                           | 13                                                                         |                                             | 13                                             | 13                                                                             |
| What is the actual number of the second page?                                                                                      | 266                                          | 240                                                                                       | 2                                                                            | 265                                                                  | The actual number of the second page is 266.                                                                      | 3070                                                                                                         | 266                                                                        | Not found                                   | 266                                            | 266                                                                            |
| What was the amount of the year-on-year increase in the largest proportion of RMB loans in November 2022?                          | 23.2 billion                                 | 9%                                                                                        | 12.40%                                                                       | 58.6 billion yuan                                                    | The largest proportion of RMB loans in November 2022 increased by 7.8%.                                           | Down by 60 billion yuan year on year (1210 billion yuan vs 1270 billion yuan)                                | 23.2 billion yuan                                                          | N/A                                         | 0.20 trillion yuan                             | 23.2 billion yuan                                                              |
| Which color is used to emphasize key text?                                                                                         | Red                                          | Blue                                                                                      | Yellow                                                                       | Red                                                                  | The color used to emphasize key text is red.                                                                      | Red                                                                                                          | Not specified.                                                             | None                                        | Red                                            | Red                                                                            |
| What is the stock code of the company discussed in the document?                                                                   | 002624                                       | HK                                                                                        | 002624                                                                       | 002624                                                               | 002624                                                                                                            | 002624                                                                                                       |                                                                            | 002624                                      | 002891.SZ                                      | 002624                                                                         |
| Which kind of companies have more workers deployed in trades irrelevent to their skills certification                              | Small companies                              | ad hoc                                                                                    | small firms                                                                  | Small companies.                                                     | smaller firms                                                                                                     | Smaller companies.                                                                                           | Small companies                                                            |                                             | Main contractor (general building) companies.  | Smaller firms.                                                                 |
| What is the required page length for manuscripts submitted?                                                                        | Between 16 and 20 pages                      | 240                                                                                       | between 16 and 20 double-spaced pages                                        | 16–20 double-spaced pages.                                           | Manuscripts should be between 16 and 20 double-spaced typed pages, with margins of at least one inch.             | Between 16 and 20 double-spaced typed pages.                                                                 | Between 16 and 20 double-spaced typed pages.                               | None                                        | 16–20 double-spaced pages.                     | 16–20 double-spaced pages.                                                     |
| What is the main underwriting amount of the company's equity financing scale in 2018?                                              | 1783                                         | 57.8                                                                                      | not answerable                                                               | 95.3 billion yuan                                                    | The main underwriting amount of the company's equity financing scale in 2018 is 541.                              | Not specified in the provided text (it appears only in the chart, which isn’t readable here).                | 91.116 billion yuan                                                        | N/A                                         | 56.6 billion yuan                              | 178.3 billion yuan                                                             |
| What is the name of the second document in the image?                                                                              | Traffic Engineering Report                   | The second document in the image is called Peachtree Industrial Boulevard.                | not answerable                                                               | Traffic Engineering Report                                           | Signal Clearance Intervals                                                                                        | PED CLEARANCE                                                                                                | Cannot be determined from the provided context.                            | 39132487.txt                                | Traffic Engineering Report                     | Traffic Engineering Report                                                     |
| What is the percentage yield of compound IX?                                                                                       | 65%                                          | 10.7%                                                                                     | 65%                                                                          | 65%                                                                  | The percentage yield of compound IX is 65%.                                                                       | Not specified in the provided information.                                                                   | Not specified.                                                             | N/A                                         | 65%                                            | 65%                                                                            |
| In which solvent are the title amides readily soluble?                                                                             | DMSO                                         | Common organic solvents but dissolve readily in DMSO.                                     | common organic solvents                                                      | DMSO                                                                 | The title amides are readily soluble in common organic solvents but dissolve readily in DMSO.                     | DMSO (dimethyl sulfoxide).                                                                                   | DMSO                                                                       | Not specified.                              | DMSO                                           | DMSO.                                                                          |
| Who is the author of "Logic as Algebra"?                                                                                           | Paul Halmos and Steven Givant                | David Greenberg                                                                           | Paul Halmos                                                                  | Paul R. Halmos and Steven Givant                                     | Paul Halmos and Steven Givant                                                                                     | Paul Halmos and Steven Givant.                                                                               | Paul R. Halmos and Steven Givant                                           | None                                        | Paul R. Halmos and Steven Givant               | Paul Halmos and Steven Givant.                                                 |
| What is the serial number associated with this package?                                                                            | 41850                                        | 00228                                                                                     | 41850                                                                        | A1850                                                                | 41850                                                                                                             | U202141850                                                                                                   | Not provided.                                                              | U202141850                                  | 41850                                          | U202141850                                                                     |
| Which knitting technique is used to join the yarn in a circle?                                                                     | Joining in Round                             | Using a bobbin of yarn                                                                    | Crochet Cast-On                                                              | Joining in the round.                                                | K2tog                                                                                                             | Join in the round (knitting in the round).                                                                   | Pass Slipped Stitch Over (PSSO) after casting on one extra stitch.         | Knitting in the round.                      | Joining in the round.                          | Joining in the round.                                                          |
| How many yards of worsted weight yarn is needed to makes 2 gloves?                                                                 | 135 yards                                    | 240 lbs                                                                                   | 135 yards/60g                                                                | 100 yards                                                            | 135 yards                                                                                                         | About 135 yards (60 g) of worsted weight yarn for a pair (2 gloves).                                         | 135 yards                                                                  | 135 yards                                   | About 150 yards.                               | 135 yards                                                                      |
| What is the unemployment rate in the year with the lowest labor force participation rate in the 16-24 age group?                   | 15%                                          | 9%                                                                                        | 6.0%                                                                         | 25%                                                                  | The unemployment rate in the year with the lowest labor force participation rate in the 16-24 age group is 13.0%. | Cannot be determined from the provided information.                                                          | 14.9%                                                                      |                                             | 10%                                            | About 15% (in 2020).                                                           |
| Around what date did the outbreak of the epidemic occur in China?                                                                  | 2022-03-04                                   | 86-10-08-90                                                                               | 2022-01-01                                                                   | Around February 2020.                                                | The outbreak of the epidemic occurred in China around 4 months ago.                                               | Around July 2022.                                                                                            | Around the first quarter of 2020.                                          |                                             | Around January 20, 2020.                       | Around March 2022.                                                             |
| What is the HTI ESG of Triangle Tyre?                                                                                              | 3.0-4.0-4.0                                  | HTI ESG of Triangle Tyre is 0-5.                                                          | Maintain Outperform                                                          | 3                                                                    | The HTI ESG of Triangle Tyre is 601163 CH.                                                                        | 3.0-4.0-4.0                                                                                                  | 3.0-4.0-4.                                                                 | 3.0-4.0-4.0                                 | BBB                                            | 3.0–4.0–4.0 (E–S–G)                                                            |
| What are the main colors of text in the document?                                                                                  | Blue and black                               | Text is blue                                                                              | white, orange, black                                                         | Black and blue.                                                      | The main colors of text in the document are black and blue.                                                       | Not specified. The provided text contains no color information, so the main text colors can’t be determined. | Not specified.                                                             |                                             | Black and blue.                                | Black and blue (with occasional gray).                                         |
| What points does SWOT refer to?                                                                                                    | Strength, weakness, opportunities, threatens | SWOT refers to the number of points a person has earned in a given year.                  | Strength, Weakness, Opportunity, Threat                                      | Strengths, Weaknesses, Opportunities, and Threats.                   | SWOT refers to Strengths, Weaknesses, Opportunities, and Threats.                                                 | Strengths, Weaknesses, Opportunities, and Threats.                                                           | Strengths, Weaknesses, Opportunities, Threats.                             | Not specified in the document.              | Strengths, Weaknesses, Opportunities, Threats. | Strengths, Weaknesses, Opportunities, and Threats.                             |
| What is the willingness of residents to travel in the first quarter of 2022?                                                       | 85.32%                                       | 0%                                                                                        | 85.32%                                                                       | 86.3%                                                                | 78%                                                                                                               | 85.32%                                                                                                       | High.                                                                      |                                             | 53.7%                                          | 85.32%                                                                         |
| How many charts are in the page 4?                                                                                                 | 2 charts                                     | 3                                                                                         | 8                                                                            | 6                                                                    | There are no charts on page 4.                                                                                    | 3                                                                                                            | 3                                                                          |                                             | 0                                              | 2                                                                              |
| What type of needle is needed for the Little Star Cowl?                                                                            | 12 mm (US 17) 16” circular needle            | A 12 mm (US 17) circular needle                                                           | Circular needle                                                              | A 16-inch circular needle.                                           | US 17) 16" circular needle                                                                                        | A 16" circular needle, size 12 mm (US 17).                                                                   | A 16-inch circular needle (12 mm/US 17).                                   | 12 mm (US 17) 16-inch circular needle.      | 12 mm (US 17) 16-inch circular needle          | A 12 mm (US 17) 16-inch circular needle.                                       |
| What color is the textile shown in the document?                                                                                   | Red                                          | Blue                                                                                      | Red                                                                          | Red                                                                  | Red                                                                                                               | Not specified.                                                                                               | Not specified.                                                             | Unknown                                     | Red                                            | Red                                                                            |
| What is the main section following 'ABBREVIATIONS'?                                                                                | CONSTRUCTION                                 | The main section following 'ABBREVIATIONS' is the main section following 'ABBREVIATIONS'. | CONSTRUCTION                                                                 | CONSTRUCTION                                                         | The main section following 'ABBREVIATIONS' is the 'SPECIFICATIONS' section.                                       | Needles.                                                                                                     | Pattern                                                                    |                                             | CONSTRUCTION                                   | CONSTRUCTION:                                                                  |
| What are the horizontal and vertical axes of Figure 4?                                                                             | Distance and densitu profile                 | The horizontal and vertical axes of Figure 4 are a horizontal and vertical axis.          | x-axis: distance, y-axis: gauss                                              | Horizontal: Orientation (degrees); Vertical: Normal error (degrees). | The horizontal axis is labeled as \( d_x \) and the vertical axis is labeled as \( d_y \).                        | Horizontal axis: Orientation angle (degrees) Vertical axis: Angular error (radians)                          | Horizontal: distance from the surface (x − x0). Vertical: density D (0–1). | Horizontal axis: None; Vertical axis: None. | x and y                                        | Horizontal: Distance x; Vertical: Density profile.                             |
| According to the current investment rating, how much does the stock rise at least relative to the Shanghai and Shenzhen 300 index? | 20%                                          | 12%                                                                                       | The stock rises at least 200 relative to the Shanghai and Shenzhen 300 index | ≥20%                                                                 | The stock rises at least 194.86% relative to the Shanghai and Shenzhen 300 index.                                 | At least 20% above the CSI 300 (Shanghai and Shenzhen 300) index.                                            | 20%                                                                        |                                             | 20%                                            | At least 20%                                                                   |
| What is the temperature range for the testing of paper chromatography reagents?                                                    | 110–120°C                                    | 10 - 20 wg.                                                                               | 0 to 20°C                                                                    | 110–120 °C                                                           | The temperature range for the testing of paper chromatography reagents is 110-120°C.                              | 20–25 °C.                                                                                                    | 110–120°C                                                                  | 110–120°C, 60–80°C, and 40–45°C.            | 110–120 °C                                     | 110–120°C                                                                      |
| What is the distribution coefficient of Benzol?                                                                                    | 160                                          | The distribution coefficient of Benzol is K.                                              | 160                                                                          | 160                                                                  | The distribution coefficient of Benzol (Benzol) is 160.                                                           | 160                                                                                                          |                                                                            | 10.4                                        | 150                                            | 160                                                                            |

The full results of MoDora and baselines are shown in [Results](./Results/resmodora.jsonl).

## 💻 MMDA Bench

MMDA is a benchmark with 537 documents and 1065 questions curated from over one million real-world documents. We perform layout-emphasize clustering to obtain these representative documents and most of them are semi-structured.
Then automatic LLM generation and manual verification are combined for QA pairs annotaion. The questions can be concered about different aspects of document (e.g. hierarchy, text, table, chart, imgae, location, formatted), to comprehensively evaluate the semi-structured document analysis performance.

You can visit it here [MMDA](./datasets/MMDA/test.json), and some documents involving sensitive data are hidden.

## 📊 Performance

The following table demonstrates the AIC-Acc and ACNLS score of different methods over MMDA Bench. The AIC-Acc and ACNLS are the modified versions of Acc and ANLS metrics respectively.

**Metric** | **ACNLS(%)** | **AIC-Acc(%)**
:---:|:---:|:---:|
 UDOP | 15.44 | 15.77 |
 DocOwl2 | 29.38 | 29.58 |
 M3DocRAG | 41.12 | 47.42 |
 SV-RAG | 33.06 | 37.75 |
 TextRAG | 29.57 | 36.24 |
 ZenDB | 36.68 | 47.14 |
 QUEST | 12.42 | 15.68 |
 GPT-5 | 41.55 | 46.48 |
 MoDora | 55.23 | 73.33 |

**Baselines**

Content extraction methods:

- [QUEST](./QUEST.zip)

Structure extraction methods:

- [ZenDB](https://github.com/Ruiying-Ma/SHTRAG)

End-to-End model methods:

- [GPT-5](https://openai.com/index/introducing-gpt-5/)

- [DocOwl2](https://github.com/X-PLUG/mPLUG-DocOwl/tree/main/DocOwl2)

- [UDOP](https://github.com/microsoft/UDOP)

Retrieval-Augmented Generation methods:

- [M3DocRAG](https://github.com/bloomberg/m3docrag/tree/main)

- [SV-RAG](https://github.com/puar-playground/Self-Visual-RAG/tree/main)

- [TextRAG](./TextRAG.zip)

## 🚀 Quick Start 

### 1. Automated Installation

We provide a one-click setup script that automatically creates a virtual environment and installs all dependencies (including PyTorch, LMDeploy, FlashAttention, and PaddleOCR):

```bash
# Grant execution permissions
chmod +x setup.sh run.sh start_backend.sh start_frontend.sh

# Run the setup script (this may take a while)
./setup.sh
```

### 2. Configuration

Before starting the services, you need to configure the backend parameters. We provide an example file [local.example.json](file:///home/yukai/project/MoDora/MoDora-backend/configs/local.example.json).

1. **Create Configuration File**:
   ```bash
   cp MoDora-backend/configs/local.example.json MoDora-backend/configs/local.json
   ```

2. **Core Configuration Items**:
   Open `MoDora-backend/configs/local.json` and modify based on your environment:
   - `api_key`: If you need to call external APIs (e.g., OpenAI or Gemini), enter your key here.
   - `llm_local_model`: Absolute path to your local model (e.g., Qwen2-VL-7B-Instruct).
   - `llm_local_instances`: Configure multiple inference instances by specifying different ports and `cuda_visible_devices` for multi-GPU parallelism.
   - `ocr_device`: Device used for OCR, e.g., `gpu:0`.

### 3. Execution

Once installation and configuration are complete, you can use `run.sh` to start both backend and frontend services simultaneously:
```bash
./run.sh
```

---

### 🛠 Manual Setup

If you prefer to set up manually:

#### 1. Backend Setup (MoDora-backend)

**Environment.**
Requires Python 3.10+.

```bash
cd MoDora-backend
# Install the package in editable mode
pip install -e .

# Install additional dependencies for OCR and LLM
# e.g., for PaddleOCR: pip install paddleocr paddlepaddle-gpu
```

**Configuration.**
MoDora-backend supports environment variables or a JSON config file (path set via `MODORA_CONFIG`).

```bash
export MODORA_API_KEY="your-api-key"
export MODORA_API_BASE="https://api.openai.com/v1"
export MODORA_API_MODEL="gpt-4o"
```

**Running the API.**
```bash
# Start FastAPI server
uvicorn modora.api.app:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup (MoDora-frontend)

**Environment.**
Requires Node.js (v20.19.0+ or v22.12.0+).

```bash
cd MoDora-frontend
npm install
```

**Running the Dev Server.**
```bash
npm run dev
```

### 3. Benchmark & Model

**Benchmark.**
Our MMDA Bench is in [MMDA](./datasets/MMDA/test.json).
For DUDE and its samples subset, refer to [DUDE](https://huggingface.co/datasets/jordyvl/DUDE_loader/tree/main/data).

**Model.**
We support both remote APIs (e.g., GPT-4o) and local models (e.g., Qwen2.5-VL, Qwen3-Embedding).
Configure model paths and settings in your environment or `config.json`.

---

## 🧪 CLI Usage (Experiments)

> **Note**: The CLI is primarily designed for experimental purposes, such as offline dataset preprocessing and batch evaluation. Before using the CLI, please ensure you have downloaded the MMDA dataset to the `datasets/MMDA` directory.

MoDora provides a comprehensive CLI for offline experiments, dataset preprocessing, and batch evaluation.

First, activate the virtual environment:
```bash
source MoDora-backend/venv/bin/activate
```

Basic usage:
```bash
# General help
modora --help

# Subcommand help
modora <command> --help
```

#### Core Commands:

1. **OCR & Component Extraction**
   Process raw PDFs to extract layout blocks and components.
   ```bash
   modora ocr --dataset datasets/MMDA --cache-dir MoDora-backend/cache_v5
   ```

2. **Tree Construction**
   Build document hierarchy trees (tree.json) from extracted components.
   ```bash
   modora build-tree --dataset datasets/MMDA --cache-dir MoDora-backend/cache_v5
   ```

3. **Single Document QA**
   Ask a question about a specific document using its constructed tree.
   ```bash
   modora qa <pdf_path> <tree_json_path> "Your question here"
   ```

4. **Batch QA Experiment**
   Run multiple questions from a dataset against the constructed trees.
   ```bash
   modora batch-qa --dataset datasets/MMDA/test.json --cache MoDora-backend/cache_v5 --output MoDora-backend/tmp
   ```

5. **Evaluation & Analysis**
   Calculate metrics (Accuracy, ANLS, ACNLS) and generate analysis charts.
   ```bash
   # By default, evaluation results and charts will be saved alongside the input file
   modora evaluate --input datasets/MMDA/test.json --result MoDora-backend/tmp/result.json
   ```
   This command will:
   - Save the detailed evaluation to `test.jsonl`.
   - Generate accuracy/ACNLS bar charts and summary CSVs in the same directory as the input.
