from openai import OpenAI
import traceback
out = r"C:\Users\Administrator\AppData\Local\hermes\logs\nvidia_test_output.txt"
try:
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="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",
    )
    resp = client.chat.completions.create(
        model="deepseek-ai/deepseek-v4-pro",
        messages=[{"role": "user", "content": "Reply with OK only"}],
        max_tokens=16,
        stream=False,
        extra_body={"chat_template_kwargs": {"thinking": False}},
    )
    txt = str(resp.choices[0].message.content)
except Exception:
    txt = "ERROR\n" + traceback.format_exc()
with open(out, "w", encoding="utf-8") as f:
    f.write(txt)
print(txt)
