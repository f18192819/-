import time
import winsound
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import os
from llm_vision import screenshot_element_and_ask

# ================= 配置与初始化 =================
try:
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=chrome_options)
except Exception as e:
    print(f"无法连接到浏览器。请确保已通过命令行启动带有调试端口的 Chrome。\n错误信息: {e}")
    exit()

# ================= 核心功能函数 =================

def alert_me():
    winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
    winsound.Beep(1200, 600)

def parse_time_to_seconds(time_str):
    if not time_str or "已完成" in time_str: return None
    match = re.search(r'(\d+):(\d+)', time_str)
    if match: return int(match.group(1)) * 60 + int(match.group(2))
    return None

def submit_smart_answer(driver, active_time_box, target_option):
    """根据 LLM 提供的答案 (target_option) 点击对应的选项并提交"""
    print(f"🚨 [自动操作] 倒计时小于 10s，准备提交大模型答案: {target_option} ...")
    try:
        container = active_time_box.find_element(By.XPATH, "./ancestor::section[contains(@class, 'slide__wrap')]")
        
        # 使用传入的 target_option (A, B, C 或 D) 构建选择器
        option_css = f'p[data-option="{target_option}"]'
        option_element = container.find_element(By.CSS_SELECTOR, option_css)
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", option_element)
        time.sleep(0.2) 
        driver.execute_script("arguments[0].click();", option_element)
        print(f"✅ 已选中选项 {target_option}")

        submit_btn = container.find_element(By.CSS_SELECTOR, 'div.submit-btn')
        time.sleep(0.3) 
        driver.execute_script("arguments[0].click();", submit_btn)
        print("✅ 答案已成功提交！")
        
        winsound.Beep(2000, 200)
    except Exception as e:
        print(f"⚠️ 自动答题失败（可能没有找到选项 {target_option}）。细节: {e}")

def update_ppt_view(driver, recorded_max_index):
    try:
        slides = driver.find_elements(By.CSS_SELECTOR, "section.timeline__item[data-index]")
        if not slides: return recorded_max_index
        
        latest_slide = max(slides, key=lambda x: int(x.get_attribute("data-index")))
        web_max_index = int(latest_slide.get_attribute("data-index"))
        
        if web_max_index > recorded_max_index:
            print(f"🔄 发现新一页 PPT (Index: {web_max_index})，正在自动同步...")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", latest_slide)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", latest_slide)
            time.sleep(1.5) 
            return web_max_index 
            
    except Exception: pass
    return recorded_max_index 

# ================= 主循环 =================

def monitor_loop():
    print(f"\n==============================================")
    print(f"🤖 全自动 AI 助教监控已启动")
    print(f"策略: [同步PPT] -> [AI识图解题] -> [倒计时<10s 自动提交答案]")
    print(f"==============================================\n")
    
    last_alert_time = 0
    last_submitted_time_text = "" 
    current_max_index = -1 
    
    # 【新增】：记录大模型已经解答过哪一题，防止死循环重复请求 API
    last_llm_solved_index = -1 
    # 【新增】：缓存当前题目的 AI 答案
    current_ai_answer = "A" 
    
    while True:
        current_max_index = update_ppt_view(driver, current_max_index)
        
        try:
            time_boxes = driver.find_elements(By.CLASS_NAME, "time-box")
            
            for box in time_boxes:
                current_time_text = box.text.strip()
                if "已完成" in current_time_text or current_time_text == "":
                    continue

                remaining_seconds = parse_time_to_seconds(current_time_text)
                
                if remaining_seconds is not None:
                    
                    # 规则 1：如果这是新的一题，立刻请求大模型，且只请求一次！
                    if current_max_index != last_llm_solved_index:
                        print(f"⏳ 正在呼叫 GLM-4.5V 求解本题...")
                        raw_answer = screenshot_element_and_ask(
                            driver=driver,
                            index=current_max_index,
                            question="请仔细阅读图中的题目，只回答一个字母，即该题正确答案，不要任何其他废话。"
                        )
                        
                        # 使用正则提取出字符串中的 A B C D，防止模型废话
                        match = re.search(r'[A-D]', raw_answer.upper())
                        if match:
                            current_ai_answer = match.group(0)
                            print(f"🧠 大模型给出答案: ---> 【 {current_ai_answer} 】 <---")
                        else:
                            current_ai_answer = "A" # 兜底策略
                            print(f"⚠️ 大模型回答格式异常 ({raw_answer})，启用兜底方案默认选 A")
                            
                        last_llm_solved_index = current_max_index # 标记为已解答，不再请求

                    # 规则 2：耳机报警
                    if time.time() - last_alert_time > 10:
                        print(f"[{time.strftime('%H:%M:%S')}] 题目进行中，剩余: {remaining_seconds}秒，AI备用答案: {current_ai_answer}")
                        alert_me()
                        last_alert_time = time.time()

                    # 规则 3：十秒极限救场（传入大模型算出来的答案）
                    if remaining_seconds <= 20 and current_time_text != last_submitted_time_text:
                        submit_smart_answer(driver, box, current_ai_answer) 
                        last_submitted_time_text = current_time_text 
                        time.sleep(3) 
                        break 

        except Exception:
            pass
        
        time.sleep(1.5) 

if __name__ == "__main__":
    try:
        monitor_loop()
    except KeyboardInterrupt:
        print("\n🛑 监控已手动停止。")