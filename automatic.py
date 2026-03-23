import time
import winsound
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

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
    """发现新题目时在耳机中响铃"""
    winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
    winsound.Beep(1200, 600)

def parse_time_to_seconds(time_str):
    """将 '01:23' 格式的文字转换为总秒数"""
    if not time_str or "已完成" in time_str:
        return None
    match = re.search(r'(\d+):(\d+)', time_str)
    if match:
        try:
            return int(match.group(1)) * 60 + int(match.group(2))
        except ValueError:
            return None
    return None

def submit_answer_a(driver, active_time_box):
    """使用相对定位：只在当前正在倒计时的这道题里找选项和按钮"""
    print("[自动操作] 时间小于 10s，尝试自动选择 A 并提交...")
    try:
        container = active_time_box.find_element(By.XPATH, "./ancestor::section[contains(@class, 'slide__wrap')]")
        
        option_a = container.find_element(By.CSS_SELECTOR, 'p[data-option="A"]')
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", option_a)
        time.sleep(0.2) 
        driver.execute_script("arguments[0].click();", option_a)
        print("✅ 已成功点击本题选项 A")

        submit_btn = container.find_element(By.CSS_SELECTOR, 'div.submit-btn')
        time.sleep(0.3) 
        driver.execute_script("arguments[0].click();", submit_btn)
        print("✅ 已成功点击本题提交答案")
        
        winsound.Beep(2000, 200)
    except Exception as e:
        print(f"自动答题失败。可能是非单选题，或选项不可见。")

def update_ppt_view(driver, recorded_max_index):
    """
    基于纯数字 index 比较。
    返回当前点击后的最新 index。
    """
    try:
        slides = driver.find_elements(By.CSS_SELECTOR, "section.timeline__item[data-index]")
        if not slides: 
            return recorded_max_index
        
        # 找出当前网页上 index 最大的那一页
        latest_slide = max(slides, key=lambda x: int(x.get_attribute("data-index")))
        web_max_index = int(latest_slide.get_attribute("data-index"))
        
        # 如果网页上的最大 index 比我们记录的还要大，说明出新课件了。
        if web_max_index > recorded_max_index:
            print(f"发现新一页 PPT (Index: {web_max_index})，正在自动同步...")
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", latest_slide)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", latest_slide)
            time.sleep(1.5) # 给右侧加载留出时间
            
            return web_max_index # 返回新的最大值，更新记录
            
    except Exception as e: 
        # print(f"切换报错: {e}") # 取消注释可查看潜在的隐藏错误
        pass
        
    return recorded_max_index # 如果没发现新页或报错，保持原有记录不变

# ================= 主循环 =================

def monitor_loop():
    print(f"\n==============================================")
    print(f"离散数学实时监控已启动")
    print(f"当前接管页面: {driver.title}")
    print(f"策略: [数字索引比对] -> [新题耳机报警] -> [<10s 自动选A提交]")
    print(f"==============================================\n")
    
    last_alert_time = 0
    last_submitted_time_text = "" 
    
    # 【新增】：用一个变量记住我们看过的最大 index，初始设为 -1
    current_max_index = -1 
    
    while True:
        # 第一步：把记录的 index 传进去，如果有新页，它会返回一个更大的数字更新记录
        current_max_index = update_ppt_view(driver, current_max_index)
        
        # 第二步：检查主界面是否有正在倒计时的习题
        try:
            time_boxes = driver.find_elements(By.CLASS_NAME, "time-box")
            
            for box in time_boxes:
                current_time_text = box.text.strip()
                
                if "已完成" in current_time_text or current_time_text == "":
                    continue

                remaining_seconds = parse_time_to_seconds(current_time_text)
                
                if remaining_seconds is not None:
                    if time.time() - last_alert_time > 10:
                        print(f"[{time.strftime('%H:%M:%S')}] 发现活跃习题，剩余时间: {remaining_seconds}秒")
                        alert_me()
                        last_alert_time = time.time()

                    if remaining_seconds <= 10 and current_time_text != last_submitted_time_text:
                        submit_answer_a(driver, box) 
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
        print("\n监控已手动停止。")