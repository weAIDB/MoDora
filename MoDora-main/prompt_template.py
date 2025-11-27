metadata_generation_prompt = """
### Instruction
I now have some data in text. Please generate {n0} nominal phrases as the keywords to comprehensively summarize the data, separated by semicolon(;).

### Data
{data}

### Note
You only need to output specified number of nominal phrases as keywords. Do not give any extra explanations.
"""

metadata_integration_prompt = """
### Instruction
I now have a group of keywords. Please select from them or summarize based on them to output {number} nominal phrases as the most comprehensive keywords, separated by semicolon(;).

### Data
{data}

### Note
You only need to output specified number of nominal phrases as keywords. Do not give any extra explanations.
"""

image_enrichment_prompt = """
### Instruction
Extract or conclude the following attributes of the image as required. Return them in the output format.

### Required Attributes
  [T] title (A short title for the image)
  [M] metadata (A few keywords as the image's metadata)
  [C] content (Describe the image content comprehensively and detailedly)

### Output Format Examples
[T] Group Photo of Participants 
[M] Group photo of ten participants; red carpet and blue background 
[C] The photo shows ten men in suits standing on the red carpet, with "the 10th Cooperation Conference" on the blue background, and ...

### Note
You only need to output the three required attributes with fixed and capitalized marks [T], [M], [C], do not miss any of them!
"""

chart_enrichment_prompt = """
### Instruction
Extract or conclude the following attributes of the chart as required. Return them in the output format.

### Required Attributes
  [T] title (A short title for the chart)
  [M] metadata (A few keywords as the chart's metadata)
  [C] content (Describe the chart content comprehensively and detailedly)

### Output Format Examples
[T] Annual Participant Trend Line Chart 
[M] A line chart of the number of participants over the years; horizontal axis by year and vertical axis by number 
[C] The line chart shows the growth trend of the participant numbers over years. The horizontal axis is the year and the vertical axis is the participant number. In 2022 there are 5 participant, in 2023 there are 7 participant, and ...

### Note
You only need to output the three required attributes with fixed and capitalized marks [T], [M], [C], do not miss any of them!
"""

table_enrichment_prompt = """
### Instruction
Extract or conclude the following attributes of the table as required. Return them in the output format.

### Required Attributes
  [T] title (A short title for the table)
  [M] metadata (A few keywords as the table's metadata)
  [C] content (Describe the table content comprehensively and detailedly)

### Output Format Examples
[T] Meeting Schedule Table 
[M] A table about the meeting schedule; three columns about activity, time and location. 
[C] Per the schedule outlined in the table, breakfast will be served at 8:00 on the 2nd floor, followed by the first meeting at 9:00 in Room 404, and then...

### Note
You only need to output the three required attributes with fixed and capitalized marks [T], [M], [C], do not miss any of them!
"""

title_extract_prompt = """
### Instruction
I now have a list of titles in the document. Please analyze title levels according to the visual pages and title semantics, and identify different levels with different number of #.
Use # for the first level title, ## for the second level title, ### for the third level title, and so on. 
Note that a higher level title leads the lower level titles following it.

### Few-shot Example
["2000", "2010", "2020"] ---> ["#2000", "#2010", "#2020"]
["Report", "Challenge", "Method", "Result"] ---> ["#Report", "##Challenge" , "##Method", "##Result"]
["Schedule", "Day1" , "Afternoon", "Night", "Day2", "Morning"] ---> ["#Schedule", "##Day1", "###Afternoon", "###Night", "##Day2", "###Morning"]

### Input List
{raw_list}

### Note
You don't need to output any additional explanations. You only need to output a new list of titles with # signs. Do not change the content and order of titles in the list.
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

check_answer_prompt = """
### Instruction
Here is a query and a reply to it. Please return T or F according to the following rules:
(1) If the reply refuses to give a valid answer by meanings like "no relevant information", "insufficient evidence", "unable to answer", "None", "N/A", output F.
(2) Otherwise output T.

### Query
{query}

### Reply
{answer}

### Note
You only need to output T or F, without any other content.
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

evaluation_prompt = """
### Instruction
Now there are the Reference answer and the generated answer to a query. Please judge whether the generated answer is correct according to the reference, output T if correct, otherwise output F.
Please mainly focuses on whether the semantics of the answers to the key parts of the query are consistent, and allows differences in the degree of detail, the sentence pattern, and the format of answers.

### Reference Answer
{a}

### Generated Answer
{b}

### Note
You only need to output T or F, without any other content.
"""

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