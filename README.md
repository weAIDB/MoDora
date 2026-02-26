# MoDora

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node ^20.19.0 || >=22.12.0](https://img.shields.io/badge/node-%5E20.19.0%20%7C%7C%20%3E%3D22.12.0-blue.svg)](https://nodejs.org/download/release/)

<img width="761" height="429" alt="5b4be666c0824062c0ef1170d7c97e1a" src="https://github.com/user-attachments/assets/1aa0d1f2-beba-4582-801c-48079602bd05" />


## 📑 Table of Contents

- [Introduction](#-introduction)
- [MMDA Bench](#-mmda-bench)
- [Performance](#-performance)
- [Quick Start](#-quick-start)
  - [1. Configuration](#1-configuration)
  - [2. Installation](#2-installation)
  - [3. Execution](#3-execution)
- [CLI Usage](#-cli-usage-experiments)


## ✨ Introduction

  MoDora is an LLM-powered framework for semi-structured document analysis. It introduces the Component-Correlation Tree (CCTree) to model semi-structured documents with diverse elements and complicated layouts. It combines preprocessing with OCR-parsed elements, tree construction and tree-based analysis, without the need for extra training or fine-tuning. The experiment on two datasets with various documents and question types demonstrates its superior performance compared to existing methods.

> - **2026.2:** Our paper "*MoDora: Tree-Based Semi-Structured Document Analysis System*" has been accepted by SIGMOD 2026.

## 📚 Features
- 🎯 **Management & Analysis**: Effectively extract document structures and features, answering user questions based on content retrival. Support multi-document management and cross-document analysis.

- 🔄 **Visualization & Integration**: Visualize the document structure (tree) and the frequency of nodes' participation in analysis (heatmap) intuitively. Users can further modify the tree structure according to their needs in the user interface.

- 👫 **Flexibility & Options**: Provide a configuration solution for flexibly adjusting backend models (local/API). And different modules can also be processed using different models.

  [![Watch on Vimeo](https://github.com/user-attachments/assets/2dcd4e49-2ec8-4ced-8789-0363503548b4)](https://vimeo.com/1167905227)


  **Examples**

  <table style="width: 100%; table-layout: fixed; font-size: 12px; border-collapse: collapse; border: 1px solid #dfe2e5; margin-bottom: 10px; word-wrap: break-word; overflow-wrap: break-word;">
    <thead><tr>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; width: 25%;">Question</th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">Answer</th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">MoDora </th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">UDOP</th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">DocOwl2</th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">M3DocRAG</th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">SV-RAG</th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">TextRAG</th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">ZenDB</th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">QUEST</th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">GPT-5</th>
    </tr></thead><tbody>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Is Bitmex launched earlier than South Korea's ban on Bitcoin derivatives?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Yes</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><details><summary><b>Yes—BitMEX launched</b></summary><b> in Jan 2014, while South Korea’s ban was on Dec 11, 2017.</b></details></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">no</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Yes</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Yes</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><details><summary>Yes, Bitmex was</summary> launched in 2014, while South Korea's ban on Bitcoin derivatives was announced in 2017.</details></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><details><summary>Yes. BitMEX launched</summary> in 2014, while South Korea’s Bitcoin derivatives ban began on 2017-12-11.</details></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Not specified.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Yes.</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What is the title at the top of the third page?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Preface</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>PREFACE</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The title of the third page is "The Changing World"</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">PREFACE</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><details><summary>2018 Global Digital</summary> Asset Derivatives Research Report</details></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><details><summary>2018 Global Digital</summary> Asset Derivatives Research Report</details></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">LEGAL NOTICES</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Digital Asset Derivatives</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Not found.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Working with Apps</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">When was this document published?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">November 30, 2023</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>November 30, 2023</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">2023 September 6, 2000</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">2023-11-10</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">2023-11-13</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><details><summary>The document was</summary> published on November 30, 2023.</details></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><details><summary>The publication date</summary> is not stated in the provided text.</details></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">November 30, 2023</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">2023-11-30</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">November 30, 2023</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What image is in the center of page 2?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">QR code</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>A QR code.</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The image is in the center of page 2.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">not answerable</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">A QR code.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">QR code</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Not specified in the provided information.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Not specified.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Not specified.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">A QR code.</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What was the decline in the electrical equipment industry last week?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">2.36%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>Down 2.36%.</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">3%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">not answerable</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">-2.36%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><details><summary>The decline in</summary> the electrical equipment industry last week was 0.6%.</details></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Down 2.36%.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Not specified in the provided context.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">-2.36%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">-3.4%</td>
      </tr>
    </tbody></table>
  <details style="margin-top: 15px; border: 1px solid #ddd; padding: 10px; border-radius: 6px;">
    <summary style="font-weight: bold; cursor: pointer; color: #0366d6;"> Click to view more examples</summary>
    <div style="margin-top: 10px;">
  <table style="width: 100%; table-layout: fixed; font-size: 12px; border-collapse: collapse; border: 1px solid #dfe2e5; margin-bottom: 10px; word-wrap: break-word; overflow-wrap: break-word;">
    <thead><tr>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; width: 25%;">Question</th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">Answer</th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">MoDora </th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">UDOP</th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">DocOwl2</th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">M3DocRAG</th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">SV-RAG</th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">TextRAG</th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">ZenDB</th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">QUEST</th>
      <th style="padding: 8px 4px; border: 1px solid #dfe2e5; background-color: #f6f8fa; font-weight: 600; text-align: left; ">GPT-5</th>
    </tr></thead><tbody>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What is the fourth section of the report?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Investment Strategy and Key Recommendations</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>Investment Strategy and Key Recommendations</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">scientific report</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">not answerable</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Risk warning</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The fourth section of the report is titled "2.2.1 New Energy Source."</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Not specified in the provided information.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Investment Strategy and Key Recommendations</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Unknown</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Real estate market</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">How many references are there?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">13</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>13</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">3</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">37</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">13</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">There are 5 references in the text.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">11</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">13</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">13</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What is the actual number of the second page?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">266</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>266</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">240</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">2</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">265</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The actual number of the second page is 266.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">3070</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">266</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Not found</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">266</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What was the amount of the year-on-year increase in the largest proportion of RMB loans in November 2022?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">23.2 billion</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>23.2 billion yuan</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">9%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">12.40%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">58.6 billion yuan</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The largest proportion of RMB loans in November 2022 increased by 7.8%.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Down by 60 billion yuan year on year (1210 billion yuan vs 1270 billion yuan)</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">23.2 billion yuan</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">N/A</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">0.20 trillion yuan</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Which color is used to emphasize key text?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Red</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>Red</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Blue</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Yellow</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Red</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The color used to emphasize key text is red.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Red</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Not specified.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">None</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Red</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What is the stock code of the company discussed in the document?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">002624</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>002624</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">HK</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">002624</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">002624</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">002624</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">002624</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">002624</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">002891.SZ</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Which kind of companies have more workers deployed in trades irrelevent to their skills certification</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Small companies</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>Smaller firms.</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">ad hoc</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">small firms</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Small companies.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">smaller firms</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Smaller companies.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Small companies</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Main contractor (general building) companies.</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What is the required page length for manuscripts submitted?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Between 16 and 20 pages</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>16–20 double-spaced pages.</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">240</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">between 16 and 20 double-spaced pages</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">16–20 double-spaced pages.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Manuscripts should be between 16 and 20 double-spaced typed pages, with margins of at least one inch.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Between 16 and 20 double-spaced typed pages.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Between 16 and 20 double-spaced typed pages.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">None</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">16–20 double-spaced pages.</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What is the main underwriting amount of the company's equity financing scale in 2018?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">1783</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>178.3 billion yuan</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">57.8</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">not answerable</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">95.3 billion yuan</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The main underwriting amount of the company's equity financing scale in 2018 is 541.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Not specified in the provided text (it appears only in the chart, which isn’t readable here).</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">91.116 billion yuan</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">N/A</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">56.6 billion yuan</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What is the name of the second document in the image?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Traffic Engineering Report</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>Traffic Engineering Report</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The second document in the image is called Peachtree Industrial Boulevard.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">not answerable</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Traffic Engineering Report</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Signal Clearance Intervals</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">PED CLEARANCE</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Cannot be determined from the provided context.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">39132487.txt</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Traffic Engineering Report</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What is the percentage yield of compound IX?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">65%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>65%</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">10.7%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">65%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">65%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The percentage yield of compound IX is 65%.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Not specified in the provided information.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Not specified.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">N/A</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">65%</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">In which solvent are the title amides readily soluble?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">DMSO</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>DMSO.</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Common organic solvents but dissolve readily in DMSO.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">common organic solvents</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">DMSO</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The title amides are readily soluble in common organic solvents but dissolve readily in DMSO.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">DMSO (dimethyl sulfoxide).</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">DMSO</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Not specified.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">DMSO</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Who is the author of "Logic as Algebra"?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Paul Halmos and Steven Givant</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>Paul Halmos and Steven Givant.</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">David Greenberg</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Paul Halmos</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Paul R. Halmos and Steven Givant</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Paul Halmos and Steven Givant</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Paul Halmos and Steven Givant.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Paul R. Halmos and Steven Givant</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">None</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Paul R. Halmos and Steven Givant</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What is the serial number associated with this package?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">41850</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>U202141850</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">00228</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">41850</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">A1850</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">41850</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">U202141850</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Not provided.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">U202141850</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">41850</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Which knitting technique is used to join the yarn in a circle?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Joining in Round</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>Joining in the round.</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Using a bobbin of yarn</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Crochet Cast-On</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Joining in the round.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">K2tog</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Join in the round (knitting in the round).</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Pass Slipped Stitch Over (PSSO) after casting on one extra stitch.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Knitting in the round.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Joining in the round.</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">How many yards of worsted weight yarn is needed to makes 2 gloves?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">135 yards</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>135 yards</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">240 lbs</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">135 yards/60g</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">100 yards</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">135 yards</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">About 135 yards (60 g) of worsted weight yarn for a pair (2 gloves).</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">135 yards</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">135 yards</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">About 150 yards.</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What is the unemployment rate in the year with the lowest labor force participation rate in the 16-24 age group?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">15%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>About 15% (in 2020).</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">9%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">6.0%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">25%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The unemployment rate in the year with the lowest labor force participation rate in the 16-24 age group is 13.0%.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Cannot be determined from the provided information.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">14.9%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">10%</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Around what date did the outbreak of the epidemic occur in China?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">2022-03-04</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>Around March 2022.</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">86-10-08-90</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">2022-01-01</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Around February 2020.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The outbreak of the epidemic occurred in China around 4 months ago.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Around July 2022.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Around the first quarter of 2020.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Around January 20, 2020.</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What is the HTI ESG of Triangle Tyre?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">3.0-4.0-4.0</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>3.0–4.0–4.0 (E–S–G)</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">HTI ESG of Triangle Tyre is 0-5.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Maintain Outperform</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">3</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The HTI ESG of Triangle Tyre is 601163 CH.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">3.0-4.0-4.0</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">3.0-4.0-4.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">3.0-4.0-4.0</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">BBB</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What are the main colors of text in the document?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Blue and black</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>Black and blue (with occasional gray).</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Text is blue</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">white, orange, black</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Black and blue.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The main colors of text in the document are black and blue.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Not specified. The provided text contains no color information, so the main text colors can’t be determined.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Not specified.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Black and blue.</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What points does SWOT refer to?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Strength, weakness, opportunities, threatens</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>Strengths, Weaknesses, Opportunities, and Threats.</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">SWOT refers to the number of points a person has earned in a given year.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Strength, Weakness, Opportunity, Threat</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Strengths, Weaknesses, Opportunities, and Threats.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">SWOT refers to Strengths, Weaknesses, Opportunities, and Threats.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Strengths, Weaknesses, Opportunities, and Threats.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Strengths, Weaknesses, Opportunities, Threats.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Not specified in the document.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Strengths, Weaknesses, Opportunities, Threats.</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What is the willingness of residents to travel in the first quarter of 2022?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">85.32%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>85.32%</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">0%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">85.32%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">86.3%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">78%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">85.32%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">High.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">53.7%</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">How many charts are in the page 4?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">2 charts</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>2</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">3</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">8</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">6</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">There are no charts on page 4.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">3</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">3</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">0</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What type of needle is needed for the Little Star Cowl?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">12 mm (US 17) 16” circular needle</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>A 12 mm (US 17) 16-inch circular needle.</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">A 12 mm (US 17) circular needle</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Circular needle</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">A 16-inch circular needle.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">US 17) 16" circular needle</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">A 16" circular needle, size 12 mm (US 17).</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">A 16-inch circular needle (12 mm/US 17).</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">12 mm (US 17) 16-inch circular needle.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">12 mm (US 17) 16-inch circular needle</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What color is the textile shown in the document?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Red</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>Red</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Blue</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Red</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Red</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Red</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Not specified.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Not specified.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Unknown</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Red</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What is the main section following 'ABBREVIATIONS'?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">CONSTRUCTION</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>CONSTRUCTION:</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The main section following 'ABBREVIATIONS' is the main section following 'ABBREVIATIONS'.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">CONSTRUCTION</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">CONSTRUCTION</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The main section following 'ABBREVIATIONS' is the 'SPECIFICATIONS' section.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Needles.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Pattern</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">CONSTRUCTION</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What are the horizontal and vertical axes of Figure 4?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Distance and densitu profile</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>Horizontal: Distance x; Vertical: Density profile.</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The horizontal and vertical axes of Figure 4 are a horizontal and vertical axis.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">x-axis: distance, y-axis: gauss</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Horizontal: Orientation (degrees); Vertical: Normal error (degrees).</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The horizontal axis is labeled as \\( d_x \\) and the vertical axis is labeled as \\( d_y \\).</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Horizontal axis: Orientation angle (degrees) Vertical axis: Angular error (radians)</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Horizontal: distance from the surface (x − x0). Vertical: density D (0–1).</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">Horizontal axis: None; Vertical axis: None.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">x and y</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">According to the current investment rating, how much does the stock rise at least relative to the Shanghai and Shenzhen 300 index?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">20%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>At least 20%</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">12%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The stock rises at least 200 relative to the Shanghai and Shenzhen 300 index</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">≥20%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The stock rises at least 194.86% relative to the Shanghai and Shenzhen 300 index.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">At least 20% above the CSI 300 (Shanghai and Shenzhen 300) index.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">20%</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">20%</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What is the temperature range for the testing of paper chromatography reagents?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">110–120°C</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>110–120°C</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">10 - 20 wg.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">0 to 20°C</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">110–120 °C</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The temperature range for the testing of paper chromatography reagents is 110-120°C.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">20–25 °C.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">110–120°C</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">110–120°C, 60–80°C, and 40–45°C.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">110–120 °C</td>
      </tr>
      <tr>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">What is the distribution coefficient of Benzol?</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">160</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"><b>160</b></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The distribution coefficient of Benzol is K.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">160</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">160</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">The distribution coefficient of Benzol (Benzol) is 160.</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">160</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;"></td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">10.4</td>
        <td style="padding: 8px 4px; border: 1px solid #dfe2e5; line-height: 1.3; vertical-align: top;">150</td>
      </tr>
    </tbody></table>
    </div></details>


  The full results of MoDora and baselines are shown in [Results](./Results/resmodora.jsonl).

## 💻 MMDA Bench

  MMDA is a benchmark with 537 documents and 1065 questions curated from over one million real-world documents. We perform layout-emphasize clustering to obtain these representative documents and most of them are semi-structured.
  Then automatic LLM generation and manual verification are combined for QA pairs annotaion. The questions can be concered about different aspects of document (e.g. hierarchy, text, table, chart, imgae, location, formatted), to comprehensively evaluate the semi-structured document analysis performance.

  You can visit it here [MMDA](./datasets/MMDA/test.json), and some documents involving sensitive data are hidden.

## 📊 Performance

  The following chart demonstrates the AIC-Acc and ACNLS score of different methods. The AIC-Acc and ACNLS are the modified versions of Acc and ANLS metrics respectively.

<img width="1566" height="463" alt="image" src="https://github.com/user-attachments/assets/003513ea-9d20-4994-b227-bfd6b327530b" />


  **Baselines**

Content extraction methods:

- [QUEST](https://arxiv.org/pdf/2507.06515)

Structure extraction methods:

- [ZenDB](https://github.com/Ruiying-Ma/SHTRAG)

- [DocAgent](https://aclanthology.org/2025.emnlp-main.893/)

End-to-End model methods:

- [GPT-5](https://openai.com/index/introducing-gpt-5/)

- [DocOwl2](https://github.com/X-PLUG/mPLUG-DocOwl/tree/main/DocOwl2)

- [UDOP](https://github.com/microsoft/UDOP)

- [LayoutLMv3](https://hf-mirror.com/rubentito/layoutlmv3-base-mpdocvqa)
 
Retrieval-Augmented Generation methods:

- [M3DocRAG](https://github.com/bloomberg/m3docrag/tree/main)

- [SV-RAG](https://github.com/puar-playground/Self-Visual-RAG/tree/main)

- [TextRAG](https://arxiv.org/pdf/2309.14389)

## 🚀 Quick Start 

### 1. Configuration

  First, grant execution permissions and initialize your configuration:

```bash
  # Grant execution permissions
  chmod +x setup.sh run.sh start_backend.sh start_frontend.sh

  # Initialize config from template
  cp local.example.json local.json
```

  Then, open `local.json` and fill in the required fields.

  **Critical configurations in local.json:**

  - **API Keys (Required)**: Ensure that the `api_key` for at least one model instance in `model_instances` (e.g., `GPT-5`) is correctly filled so that the system can run.
  - **Vector Search (Optional)**: If you enable `enable_vector_search`, you MUST fill in `embedding_api_key` (and `rerank_api_key` if a rerank model is used). These are not required if vector search is disabled.

### 2. Installation

  We provide a one-click setup script that automatically creates a virtual environment and installs all dependencies (including PyTorch, LMDeploy, FlashAttention, and PaddleOCR):

```bash
  # Run the setup script (this may take a while)
  ./setup.sh
```

  Local models are NOT automatically downloaded. By default, MoDora uses remote models (GPT-5). 

  > **Recommendation**: If you have a GPU with **24GB+ VRAM**, we highly recommend using **Qwen-3-VL-8B-Instruct** as a local model for better performance and privacy.

  To use a local model, download it and update your `local.json`:

```bash
  # Activate venv after setup.sh
  source MoDora-backend/venv/bin/activate

  # Download recommendation: Qwen-3-VL-8B-Instruct
  python download_model.py --repo_id Qwen/Qwen3-VL-8B-Instruct --local_dir ./MoDora-backend/models/Qwen3-VL-8B-Instruct
```

  **Update `local.json` Example:**

```json
  "model_instances": {
    "Qwen3-VL-8B-Instruct": {
      "type": "local",
      "model": "MoDora-backend/models/Qwen3-VL-8B-Instruct",
      "port": 9001,
      "device": "0"
    }
  },
  "ui_settings": {
    "pipelines": {
      "enrichment": { "modelInstance": "Qwen3-VL-8B-Instruct" },
      "retriever": { "modelInstance": "Qwen3-VL-8B-Instruct" }
    }
  }
```

### 3. Execution

  Once installation and configuration are complete, you can use `run.sh` to start both backend and frontend services simultaneously:

```bash
  ./run.sh
```

  Alternatively, you can start the backend and frontend separately in two terminal tabs:

```bash
  # Terminal 1: Backend
  ./start_backend.sh

  # Terminal 2: Frontend
  ./start_frontend.sh
```

  > **Note on Ports**: Both scripts automatically detect the API port from `local.json` (defaulting to `8005`). This ensures the frontend proxy correctly points to the backend even when started manually. You can customize the port by modifying the `"api_port"` field in your `local.json`.

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

### Core Commands:

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
     # By default, evaluation results and charts will be saved alongside the result.json file
     modora evaluate --input datasets/MMDA/test.json --result MoDora-backend/tmp/result.json
     ```

     This command will:

     - Update `result.json` with calculated metrics (Accuracy, ANLS, etc.).
     - Save the detailed evaluation to `evaluation.jsonl` in the same directory as `result.json`.
     - Generate accuracy/ACNLS bar charts and summary CSVs in the same directory.
