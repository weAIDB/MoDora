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
