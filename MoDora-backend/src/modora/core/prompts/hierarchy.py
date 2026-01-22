level_title_prompt = """
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
