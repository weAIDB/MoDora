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
