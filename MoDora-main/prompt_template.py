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