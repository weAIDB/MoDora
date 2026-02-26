metadata_generation_prompt = """
### Instruction
I now have some data in text. Please generate {num} nominal phrases as the keywords to comprehensively summarize the data, separated by semicolon(;).

### Data
{data}

### Note
You only need to output specified number of nominal phrases as keywords. Do not give any extra explanations.
"""

metadata_integration_prompt = """
### Instruction
I now have a group of keywords. Please select from them or summarize based on them to output {num} nominal phrases as the most comprehensive keywords, separated by semicolon(;).

### Data
{data}

### Note
You only need to output specified number of nominal phrases as keywords. Do not give any extra explanations.
"""
