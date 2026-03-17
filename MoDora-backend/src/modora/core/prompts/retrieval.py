from __future__ import annotations

question_parsing_prompt = """
### Instructions:
Now we have a question about a PDF report. Before answering, you are expected to divide the quetion into two parts: the location information and the content information.

The location information **MUST** be output as a standard JSON list of dictionaries, following this structure:
`[ {"page":X, "grid":["(r1, c1)", "(r2, c2)", ...]} ]`
**NOTE: All strings (including coordinates) MUST use double quotes ("") and coordinates MUST be represented as a quoted string of a Python tuple, e.g., "(r, c)".**

**Conversion Rules for Location (r: row, c: column):**
1.  The page is divided into a 3x3 grid:
    - Row (r): top=1, middle=2, bottom=3.
    - Column (c): left=1, center=2, right=3.
2.  Use the exact **quoted string "(r, c)"** for specific locations. (e.g., "top center" is **"(1, 2)"**).
3.  If the location is **not specified** (e.g., the question asks for a full page or a whole section), the "grid" list must be **empty** (`[]`).
4.  The page number counted from the end is represented by a negative number. (e.g., "the last page" is page -1).
5.  If **no page number is mentioned** (e.g., "What is the report's conclusion?"), set the "page" value to **0**.
6.  If only row or column is mentioned (e.g., "top" or "left"), include **all relevant grid coordinates**. For example, "top" translates to `["(1, 1)", "(1, 2)", "(1, 3)"]`.
7.  If only "center" or "middle" is mentioned, it translates to `["(2, 2)"]`, but "center column" or "middle row" still requires all relevant coordinates.
8.  For multiple locations, include multiple dictionaries in the list.
9.  If the question contains discriptions like header, footer, title, caption, figure, table, section, paragraph, image, chart, graph, diagram, etc., these are all considered content-related and should not affect the location extraction.

The content information includes the other specific question about the content. The locations should be replaced by use general terms like 'here', 'there', 'these places'.
The output format for each question MUST be:

-question: [Original Question]
-location: [JSON LIST HERE]
-content: [Parsed Content Question]

### Few-Shot Examples:
1.  -question:  What is the title at the top of page 3?
    -location:  [ {"page":3, "grid":["(1, 1)", "(1, 2)", "(1, 3)"]} ]
    -content:   What is the title here?
2.  -question:  What is the heading on the first page and the forth page?
    -location:  [ {"page":1, "grid":[]}, {"page":4, "grid":[]} ]
    -content:   What is the heading these places?
3.  -question:  What is the fourth section of the report?
    -location:  [ {"page":0, "grid":[]} ]
    -content:   What is the fourth section of the report?
4.  -question:  What is the image shown at the center of page 2 and the text at the bottom right of page 5?
    -location:  [ {"page":2, "grid":["(2, 2)"]}, {"page":5, "grid":["(3, 3)"]} ]
    -content:   What is the image here and the text there?
5.  -question:  What is the title of the last two pages?
    -location:  [ {"page":-2, "grid":[]}, {"page":-1, "grid":[]} ]
    -content:   What is the title these places?

### Input Questions:
__QUESTION_PLACEHOLDER__

### Note:
You don't need to output any additional explanations. Please strictly follow the output format.
"""

select_children_prompt = """
### Instruction
I now have a query about the document, and another list contains the titles of some paragraphs in the document. They have the same superior path and different metadata.
Please return titles that may contain potential or direct evidence in its corresponding paragraphs, as a list, based on the analysis of the superior path and metadata map.
The returned list may be the input list itself, a subset of it, or empty.

### Query
{query}

### List
{list}

### Superior Path
{path}

### Metadata Map
{metadata_map}

### Note
You don't need to output any additional explanations or annotations. You only need to output a list of selected titles.
"""

check_node_prompt1 = """
### Instruction
Now I have a query and some text. Please judge whether the text contains evidence pieces or cues about the query.
Some cues may not directly provide the answer but is important for reasoning.
If yes, output T, otherwise output F.

### Query
{query}

### Text
{data}

### Note
You only need to output T or F, without any other content.
"""

check_node_prompt2 = """
### Instruction
Now I have a query. Given the visual image of certain areas of a document and the corresponding text, please judge whether the image or text contains evidences or cues about the query.
Some cues may not directly provide the answer but is important for reasoning.
If yes, output T, otherwise output F.

### Query
{query}

### Text
{data}

### Note
You only need to output T or F, without any other content.
"""

rerank_prompt = """
### Instruction
Given a query and a passage, output a relevance score between 0 and 1. The score should reflect how likely the passage contains evidence needed to answer the query.
Only output the score as a number.

### Query
{query}

### Passage
{passage}
"""

image_reasoning_prompt = """
### Instruction
Now we have a query and a document. Given the document schema, the textual evidence pieces retrieved from it and the visual image of their corresponding areas, please return a short and concise answer to the query.

### Query
{query}

### Schema
{schema}

### Evidence
{evidence}

### Note
You only need to output a short and concise answer. Do not add any explanations or repeat the query content in the output answer.
"""

retrieved_reasoning_prompt = """
### Instruction
Now we have a query and a document. Given the document schema, the textual evidence pieces retrieved from it and the visual image of their corresponding areas, please return a short and concise answer to the query.

### Query
{query}

### Schema
{schema}

### Evidence
{evidence}

### Note
You only need to output a short and concise answer. Do not add any explanations or repeat the query content in the output answer.
"""

whole_reasoning_prompt = """
### Instruction
Now we have a query, please answer it based on the given visual pages and tree format of a document. Return a short and concise answer.

### Query
{query}

### Document Tree
{data}

### Note
You only need to output a short and concise answer. Do not add any explanations or repeat the query content in the output answer.
"""

location_extraction_prompt = """
### Instruction
Now I have a query, please determine whether there are cues about the location of elements in the document, including:
1. **Page number**: Extract the page numbers needed by the query as a list. For example:
   - "the first page" ---> [1]
   - "page 6" ---> [6]
   - "the first three pages" ---> [1, 2, 3]
   If no page number is mentioned, return [-1].

2. **Position on the page**: Divide the page into a 3x3 grid (9 blocks) and extract the position as a two-element vector [row, column]:
   - The first element (row) represents vertical position:
     - "top" ---> 1
     - "middle" ---> 2
     - "bottom" ---> 3
     - If vertical position is not mentioned, return -1.
   - The second element (column) represents horizontal position:
     - "left" ---> 1
     - "center" ---> 2
     - "right" ---> 3
     - If horizontal position is not mentioned, return -1.
   If both vertical and horizontal positions are missing, return [-1, -1].

### Output Format
Page: [page_numbers]; Position: [row, column]

### Few-Shot Example
"What is written on the top right corner of the first page?" ---> Page: [1]; Position: [1, 3]

"What is written on page 6 at the bottom center?" ---> Page: [6]; Position: [3, 2]

"How many images are in the first three pages?" ---> Page: [1, 2, 3]; Position: [-1, -1]

"What is the title of the document?" ---> Page: [-1]; Position: [-1, -1]

"When will the meeting in Room 404 be held?" ---> Page: [-1]; Position: [-1, -1]

### Query
{query}

### Note
You only need to output the location cues found in the query with the specified format. Do not add any extra explanations.
"""
