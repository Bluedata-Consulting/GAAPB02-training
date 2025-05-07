from pathlib import Path
filename = "prompts/system_prompt.txt"
_SYSTEM_PROMPT = Path(filename).read_text(encoding='utf-8')


def build_prompt(card:str, history:list[str],query:str)->list[dict]:
    messages = [{"role":"system","content":_SYSTEM_PROMPT + card}]
    for i in range(0,len(history),2):
        messages.append({"role":"user","content":history[i]})
        messages.append({"role":"assistant","content":history[i+1]})
    messages.append({"role":"user","content":query})
    return messages