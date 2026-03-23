"""
llm_vision.py
将屏幕截图（文件路径或 Selenium 元素）发送给 GLM-4.5V，返回模型回答。
"""

import base64
import os
import openai
from dotenv import load_dotenv

load_dotenv()

# ================= 配置 =================
API_KEY = os.environ["GLM_API_KEY"]
BASE_URL = os.environ["GLM_BASE_URL"]
MODEL = os.environ.get("GLM_MODEL", "GLM-4.5V")

client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL)


# ================= 工具函数 =================

def image_to_base64(image_path: str) -> str:
    """将本地图片文件编码为 base64 data URL。"""
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    ext = os.path.splitext(image_path)[-1].lstrip(".").lower()
    mime = "image/png" if ext == "png" else f"image/{ext}"
    return f"data:{mime};base64,{data}"


def ask_llm_with_image(image_path: str, question: str = "请仔细阅读图中的题目，只回答一个字母（A\B\C\D中其中一个）即该题正确答案") -> str:
    """
    将本地截图发送给 GLM-4.5V，返回模型的文字回答。

    Args:
        image_path: 本地图片文件路径（PNG / JPG）。
        question:   随图发送的文字提示。

    Returns:
        模型返回的字符串答案，出错时返回空字符串。
    """
    try:
        image_url = image_to_base64(image_path)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": question},
                    ],
                }
            ],
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        print(f"[llm_vision] 调用失败: {e}")
        return ""


def screenshot_element_and_ask(driver, index: int, question: str = "请仔细阅读图中的题目，给出正确选项及简要理由。") -> str:
    """
    对 Selenium WebElement 截图，保存后发送给 LLM。

    Args:
        driver: 电脑屏幕。
        index:   题目序号，用于命名截图文件。
        question: 随图发送的文字提示。

    Returns:
        模型返回的字符串答案。
    """
    save_path = os.path.join(os.getcwd(), f"question_{index}.png")
    try:
        driver.save_screenshot(save_path)
        print(f"[llm_vision] 截图已保存: {save_path}")
    except Exception as e:
        print(f"[llm_vision] 截图失败: {e}")
        return ""

    return ask_llm_with_image(save_path, question)


# # ================= 独立运行测试 =================

# if __name__ == "__main__":
#     import sys

#     if len(sys.argv) < 2:
#         print("用法: python llm_vision.py <图片路径> [问题文字]")
#         print("示例: python llm_vision.py question_0.png")
#         sys.exit(1)

#     path = sys.argv[1]
#     q = sys.argv[2] if len(sys.argv) >= 3 else "请仔细阅读图中的题目，给出正确选项及简要理由。"
#     answer = ask_llm_with_image(path, q)
#     print("\n===== LLM 回答 =====")
#     print(answer)
