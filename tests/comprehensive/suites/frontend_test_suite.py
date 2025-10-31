"""
前端测试套件
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

from ..core.test_controller import TestSuite
from ..core.test_result import TestResult, TestSuiteResult, TestStatus, ResultType
from ..config.test_config import TestConfiguration
from ..utils.helpers import retry_on_failure, timeout_after
from ..utils.logging_utils import get_logger


class FrontendTestSuite(TestSuite):
    """前端测试套件"""
    
    def __init__(self, name: str, config: TestConfiguration):
        super().__init__(name, config)
        self.logger = get_logger("frontend_test")
        self.driver = None
        self.page_objects = {}
    
    async def run_all_tests(self) -> TestSuiteResult:
        """运行所有前端测试"""
        self.logger.info("🌐 开始前端测试套件")
        
        suite_result = TestSuiteResult(
            suite_name=self.name,
            start_time=datetime.now()
        )
        
        # 检查是否可以运行前端测试
        if not await self._check_frontend_test_prerequisites():
            self.logger.warning("前端测试环境不满足要求，跳过前端测试")
            
            # 创建跳过的测试结果
            skipped_result = self.create_test_result("frontend_tests_skipped")
            skipped_result.status = TestStatus.SKIPPED
            skipped_result.details = {"reason": "Frontend test environment not available"}
            suite_result.add_result(skipped_result)
            
            suite_result.end_time = datetime.now()
            return suite_result
        
        try:
            # 设置测试环境
            await self._setup_test_environment()
            
            # 定义测试用例
            test_cases = [
                ("page_load", self._test_page_load),
                ("navigation", self._test_navigation),
                ("agent_management", self._test_agent_management),
                ("task_creation", self._test_task_creation),
                ("llm_configuration", self._test_llm_configuration)
            ]
            
            # 执行测试用例
            for test_name, test_func in test_cases:
                result = await self._run_single_test(test_name, test_func)
                suite_result.add_result(result)
            
        finally:
            # 清理测试环境
            await self._cleanup_test_environment()
        
        suite_result.end_time = datetime.now()
        suite_result.calculate_duration()
        
        self.logger.info(f"🌐 前端测试套件完成: {suite_result.passed_tests}/{suite_result.total_tests} 通过")
        
        return suite_result
    
    async def _check_frontend_test_prerequisites(self) -> bool:
        """检查前端测试先决条件"""
        try:
            # 检查是否可以导入selenium
            import selenium
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            # 检查Chrome是否可用
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            
            # 尝试创建WebDriver实例
            try:
                driver = webdriver.Chrome(options=chrome_options)
                driver.quit()
                return True
            except Exception as e:
                self.logger.warning(f"Chrome WebDriver不可用: {e}")
                return False
                
        except ImportError as e:
            self.logger.warning(f"Selenium未安装: {e}")
            return False
    
    async def _setup_test_environment(self):
        """设置测试环境"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            # 配置Chrome选项
            chrome_options = Options()
            
            # 获取配置
            suite_config = self.config.test_suites.get("frontend_tests", {})
            headless = suite_config.get("headless", True)
            
            if headless:
                chrome_options.add_argument("--headless")
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            
            # 创建WebDriver实例
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)  # 隐式等待10秒
            
            self.logger.info("前端测试环境设置完成")
            
        except Exception as e:
            self.logger.error(f"设置前端测试环境失败: {e}")
            raise
    
    async def _cleanup_test_environment(self):
        """清理测试环境"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.logger.info("前端测试环境清理完成")
            except Exception as e:
                self.logger.warning(f"清理前端测试环境时出现警告: {e}")
    
    async def _run_single_test(self, test_name: str, test_func) -> TestResult:
        """运行单个测试"""
        result = self.create_test_result(test_name)
        result.start_time = datetime.now()
        result.result_type = ResultType.FUNCTIONAL
        result.tags = ["frontend", "ui"]
        
        self.logger.test_start(test_name)
        
        try:
            success, details = await test_func()
            
            result.end_time = datetime.now()
            result.calculate_duration()
            
            if success:
                result.set_success(details)
                self.logger.test_end(test_name, True, result.duration)
            else:
                error_msg = details.get("error", "Unknown error") if isinstance(details, dict) else str(details)
                result.set_error(error_msg)
                self.logger.test_end(test_name, False, result.duration)
            
            # 添加性能指标
            if "load_time" in details:
                result.add_metric("page_load_time", details["load_time"], "s", 10.0)
            
        except Exception as e:
            result.end_time = datetime.now()
            result.calculate_duration()
            result.set_error(str(e))
            self.logger.error_detail(e, {"test_name": test_name})
        
        return result
    
    @timeout_after(60.0)
    async def _test_page_load(self) -> Tuple[bool, Dict[str, Any]]:
        """测试页面加载"""
        self.logger.test_step("测试主页面加载")
        
        if not self.driver:
            return False, {"error": "WebDriver not initialized"}
        
        try:
            start_time = time.time()
            
            # 访问主页面
            main_url = f"{self.config.frontend_url}/88.html"
            self.driver.get(main_url)
            
            # 等待页面加载完成
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            
            wait = WebDriverWait(self.driver, 30)
            
            # 等待body元素出现
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            load_time = time.time() - start_time
            
            # 检查页面基本信息
            page_title = self.driver.title
            current_url = self.driver.current_url
            page_source_length = len(self.driver.page_source)
            
            # 检查关键元素
            key_elements = {}
            
            try:
                # 检查HTML结构
                html_element = self.driver.find_element(By.TAG_NAME, "html")
                key_elements["html"] = html_element is not None
                
                head_element = self.driver.find_element(By.TAG_NAME, "head")
                key_elements["head"] = head_element is not None
                
                body_element = self.driver.find_element(By.TAG_NAME, "body")
                key_elements["body"] = body_element is not None
                
                # 检查是否有JavaScript错误
                logs = self.driver.get_log('browser')
                js_errors = [log for log in logs if log['level'] == 'SEVERE']
                
            except Exception as e:
                key_elements["error"] = str(e)
                js_errors = []
            
            # 判断加载是否成功
            success = (
                page_source_length > 100 and  # 页面有内容
                key_elements.get("html", False) and
                key_elements.get("body", False) and
                load_time < 30.0  # 加载时间合理
            )
            
            details = {
                "load_time": load_time,
                "page_title": page_title,
                "current_url": current_url,
                "page_source_length": page_source_length,
                "key_elements": key_elements,
                "js_errors_count": len(js_errors),
                "js_errors": js_errors[:5] if js_errors else []  # 只保留前5个错误
            }
            
            if success:
                self.logger.test_step(f"页面加载成功 - 加载时间: {load_time:.3f}s, 标题: {page_title}")
            else:
                self.logger.test_step(f"页面加载失败 - 加载时间: {load_time:.3f}s")
            
            return success, details
            
        except Exception as e:
            return False, {"error": str(e), "error_type": type(e).__name__}
    
    @timeout_after(45.0)
    async def _test_navigation(self) -> Tuple[bool, Dict[str, Any]]:
        """测试页面导航"""
        self.logger.test_step("测试页面导航功能")
        
        if not self.driver:
            return False, {"error": "WebDriver not initialized"}
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            navigation_results = {}
            
            # 测试页面列表
            test_pages = [
                ("main_page", f"{self.config.frontend_url}/88.html", "主页面"),
                ("test_page", f"{self.config.frontend_url}/test.html", "测试页面"),
                ("enhanced_page", f"{self.config.frontend_url}/enhanced-index.html", "增强页面")
            ]
            
            successful_navigations = 0
            
            for page_key, url, description in test_pages:
                try:
                    start_time = time.time()
                    
                    self.driver.get(url)
                    
                    # 等待页面加载
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    
                    navigation_time = time.time() - start_time
                    
                    # 检查页面是否正确加载
                    current_url = self.driver.current_url
                    page_title = self.driver.title
                    
                    success = (
                        current_url.endswith(url.split('/')[-1]) and
                        len(self.driver.page_source) > 100 and
                        navigation_time < 15.0
                    )
                    
                    navigation_results[page_key] = {
                        "success": success,
                        "url": url,
                        "description": description,
                        "navigation_time": navigation_time,
                        "current_url": current_url,
                        "page_title": page_title
                    }
                    
                    if success:
                        successful_navigations += 1
                        self.logger.test_step(f"✅ {description} 导航成功 - {navigation_time:.3f}s")
                    else:
                        self.logger.test_step(f"❌ {description} 导航失败")
                        
                except Exception as e:
                    navigation_results[page_key] = {
                        "success": False,
                        "url": url,
                        "description": description,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                    self.logger.test_step(f"❌ {description} 导航异常: {e}")
            
            # 测试浏览器导航功能
            try:
                # 测试后退功能
                if len(test_pages) > 1:
                    self.driver.back()
                    time.sleep(1)
                    
                    # 测试前进功能
                    self.driver.forward()
                    time.sleep(1)
                    
                    navigation_results["browser_navigation"] = {
                        "back_forward": True,
                        "success": True
                    }
                else:
                    navigation_results["browser_navigation"] = {
                        "back_forward": False,
                        "reason": "Not enough pages to test"
                    }
                    
            except Exception as e:
                navigation_results["browser_navigation"] = {
                    "success": False,
                    "error": str(e)
                }
            
            # 计算总体成功率
            total_pages = len(test_pages)
            success_rate = (successful_navigations / total_pages * 100) if total_pages > 0 else 0
            overall_success = success_rate >= 70  # 70%以上成功率算通过
            
            summary = {
                "total_pages": total_pages,
                "successful_navigations": successful_navigations,
                "success_rate": success_rate,
                "navigation_results": navigation_results
            }
            
            return overall_success, summary
            
        except Exception as e:
            return False, {"error": str(e), "error_type": type(e).__name__}
    
    @timeout_after(90.0)
    async def _test_agent_management(self) -> Tuple[bool, Dict[str, Any]]:
        """测试智能体管理界面"""
        self.logger.test_step("测试智能体管理界面")
        
        if not self.driver:
            return False, {"error": "WebDriver not initialized"}
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # 访问主页面
            main_url = f"{self.config.frontend_url}/88.html"
            self.driver.get(main_url)
            
            # 等待页面加载
            wait = WebDriverWait(self.driver, 30)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            agent_management_results = {}
            
            # 查找智能体相关的元素
            try:
                # 查找可能的智能体管理元素
                agent_elements = []
                
                # 通过不同的选择器查找智能体相关元素
                selectors = [
                    "//button[contains(text(), '智能体')]",
                    "//button[contains(text(), 'Agent')]",
                    "//div[contains(@class, 'agent')]",
                    "//span[contains(text(), '智能体')]",
                    "//*[contains(@id, 'agent')]"
                ]
                
                for selector in selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        agent_elements.extend(elements)
                    except:
                        continue
                
                agent_management_results["agent_elements_found"] = len(agent_elements)
                
                # 如果找到智能体相关元素，尝试交互
                if agent_elements:
                    # 尝试点击第一个智能体相关元素
                    first_element = agent_elements[0]
                    
                    # 检查元素是否可见和可点击
                    if first_element.is_displayed() and first_element.is_enabled():
                        first_element.click()
                        time.sleep(2)  # 等待响应
                        
                        agent_management_results["interaction_successful"] = True
                        agent_management_results["clicked_element"] = {
                            "tag": first_element.tag_name,
                            "text": first_element.text[:50],  # 限制文本长度
                            "class": first_element.get_attribute("class")
                        }
                    else:
                        agent_management_results["interaction_successful"] = False
                        agent_management_results["reason"] = "Element not clickable"
                else:
                    agent_management_results["interaction_successful"] = False
                    agent_management_results["reason"] = "No agent elements found"
                
            except Exception as e:
                agent_management_results["interaction_error"] = str(e)
            
            # 检查页面是否有智能体相关的内容
            page_source = self.driver.page_source.lower()
            
            agent_keywords = ["智能体", "agent", "meta", "coordinator", "decomposer"]
            found_keywords = [keyword for keyword in agent_keywords if keyword in page_source]
            
            agent_management_results["agent_keywords_found"] = found_keywords
            agent_management_results["has_agent_content"] = len(found_keywords) > 0
            
            # 检查是否有相关的JavaScript功能
            try:
                # 执行JavaScript检查
                js_check = """
                return {
                    hasAgentManager: typeof window.agentManager !== 'undefined',
                    hasAgentFunctions: typeof window.loadAgents === 'function' || typeof window.updateAgentStatus === 'function',
                    agentRelatedVars: Object.keys(window).filter(key => key.toLowerCase().includes('agent')).slice(0, 5)
                };
                """
                
                js_result = self.driver.execute_script(js_check)
                agent_management_results["javascript_features"] = js_result
                
            except Exception as e:
                agent_management_results["javascript_check_error"] = str(e)
            
            # 判断测试是否成功
            success = (
                agent_management_results.get("agent_elements_found", 0) > 0 or
                agent_management_results.get("has_agent_content", False) or
                agent_management_results.get("javascript_features", {}).get("hasAgentManager", False)
            )
            
            if success:
                self.logger.test_step("智能体管理界面测试通过")
            else:
                self.logger.test_step("智能体管理界面测试失败 - 未找到相关功能")
            
            return success, agent_management_results
            
        except Exception as e:
            return False, {"error": str(e), "error_type": type(e).__name__}
    
    @timeout_after(90.0)
    async def _test_task_creation(self) -> Tuple[bool, Dict[str, Any]]:
        """测试任务创建界面"""
        self.logger.test_step("测试任务创建界面")
        
        if not self.driver:
            return False, {"error": "WebDriver not initialized"}
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            task_creation_results = {}
            
            # 查找任务创建相关的元素
            try:
                # 查找可能的任务创建元素
                task_elements = []
                
                selectors = [
                    "//button[contains(text(), '创建任务')]",
                    "//button[contains(text(), '新建任务')]",
                    "//button[contains(text(), 'Create Task')]",
                    "//input[@placeholder*='任务']",
                    "//textarea[@placeholder*='任务']",
                    "//*[contains(@id, 'task')]",
                    "//form[contains(@class, 'task')]"
                ]
                
                for selector in selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        task_elements.extend(elements)
                    except:
                        continue
                
                task_creation_results["task_elements_found"] = len(task_elements)
                
                # 查找表单元素
                form_elements = {
                    "inputs": len(self.driver.find_elements(By.TAG_NAME, "input")),
                    "textareas": len(self.driver.find_elements(By.TAG_NAME, "textarea")),
                    "selects": len(self.driver.find_elements(By.TAG_NAME, "select")),
                    "buttons": len(self.driver.find_elements(By.TAG_NAME, "button"))
                }
                
                task_creation_results["form_elements"] = form_elements
                
                # 尝试填写表单（如果存在）
                if task_elements:
                    try:
                        # 查找输入框
                        inputs = self.driver.find_elements(By.TAG_NAME, "input")
                        textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
                        
                        filled_fields = 0
                        
                        # 尝试填写文本输入框
                        for input_elem in inputs[:3]:  # 最多填写3个输入框
                            if input_elem.is_displayed() and input_elem.is_enabled():
                                input_type = input_elem.get_attribute("type")
                                if input_type in ["text", "email", None]:
                                    input_elem.clear()
                                    input_elem.send_keys("测试任务")
                                    filled_fields += 1
                        
                        # 尝试填写文本区域
                        for textarea in textareas[:2]:  # 最多填写2个文本区域
                            if textarea.is_displayed() and textarea.is_enabled():
                                textarea.clear()
                                textarea.send_keys("这是一个测试任务的描述")
                                filled_fields += 1
                        
                        task_creation_results["form_interaction"] = {
                            "filled_fields": filled_fields,
                            "success": filled_fields > 0
                        }
                        
                    except Exception as e:
                        task_creation_results["form_interaction"] = {
                            "error": str(e),
                            "success": False
                        }
                
            except Exception as e:
                task_creation_results["element_search_error"] = str(e)
            
            # 检查页面内容
            page_source = self.driver.page_source.lower()
            
            task_keywords = ["任务", "task", "创建", "create", "新建", "new"]
            found_keywords = [keyword for keyword in task_keywords if keyword in page_source]
            
            task_creation_results["task_keywords_found"] = found_keywords
            task_creation_results["has_task_content"] = len(found_keywords) > 0
            
            # 检查JavaScript功能
            try:
                js_check = """
                return {
                    hasTaskManager: typeof window.taskManager !== 'undefined',
                    hasTaskFunctions: typeof window.createTask === 'function' || typeof window.submitTask === 'function',
                    taskRelatedVars: Object.keys(window).filter(key => key.toLowerCase().includes('task')).slice(0, 5)
                };
                """
                
                js_result = self.driver.execute_script(js_check)
                task_creation_results["javascript_features"] = js_result
                
            except Exception as e:
                task_creation_results["javascript_check_error"] = str(e)
            
            # 判断测试是否成功
            success = (
                task_creation_results.get("task_elements_found", 0) > 0 or
                task_creation_results.get("form_elements", {}).get("inputs", 0) > 0 or
                task_creation_results.get("has_task_content", False)
            )
            
            if success:
                self.logger.test_step("任务创建界面测试通过")
            else:
                self.logger.test_step("任务创建界面测试失败 - 未找到相关功能")
            
            return success, task_creation_results
            
        except Exception as e:
            return False, {"error": str(e), "error_type": type(e).__name__}
    
    @timeout_after(90.0)
    async def _test_llm_configuration(self) -> Tuple[bool, Dict[str, Any]]:
        """测试LLM配置界面"""
        self.logger.test_step("测试LLM配置界面")
        
        if not self.driver:
            return False, {"error": "WebDriver not initialized"}
        
        try:
            from selenium.webdriver.common.by import By
            
            llm_config_results = {}
            
            # 查找LLM配置相关的元素
            try:
                llm_elements = []
                
                selectors = [
                    "//button[contains(text(), 'LLM')]",
                    "//button[contains(text(), '配置')]",
                    "//button[contains(text(), 'Config')]",
                    "//*[contains(text(), '大模型')]",
                    "//*[contains(@id, 'llm')]",
                    "//*[contains(@class, 'config')]"
                ]
                
                for selector in selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        llm_elements.extend(elements)
                    except:
                        continue
                
                llm_config_results["llm_elements_found"] = len(llm_elements)
                
                # 查找配置相关的输入框
                config_inputs = []
                
                config_selectors = [
                    "//input[@placeholder*='API']",
                    "//input[@placeholder*='Key']",
                    "//input[@placeholder*='Token']",
                    "//input[@placeholder*='URL']",
                    "//input[@type='password']"
                ]
                
                for selector in config_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        config_inputs.extend(elements)
                    except:
                        continue
                
                llm_config_results["config_inputs_found"] = len(config_inputs)
                
            except Exception as e:
                llm_config_results["element_search_error"] = str(e)
            
            # 检查页面内容
            page_source = self.driver.page_source.lower()
            
            llm_keywords = ["llm", "大模型", "配置", "config", "api", "key", "token", "model"]
            found_keywords = [keyword for keyword in llm_keywords if keyword in page_source]
            
            llm_config_results["llm_keywords_found"] = found_keywords
            llm_config_results["has_llm_content"] = len(found_keywords) > 0
            
            # 检查JavaScript功能
            try:
                js_check = """
                return {
                    hasLLMConfig: typeof window.llmConfig !== 'undefined',
                    hasConfigFunctions: typeof window.saveLLMConfig === 'function' || typeof window.loadLLMConfig === 'function',
                    configRelatedVars: Object.keys(window).filter(key => 
                        key.toLowerCase().includes('llm') || 
                        key.toLowerCase().includes('config')
                    ).slice(0, 5)
                };
                """
                
                js_result = self.driver.execute_script(js_check)
                llm_config_results["javascript_features"] = js_result
                
            except Exception as e:
                llm_config_results["javascript_check_error"] = str(e)
            
            # 判断测试是否成功
            success = (
                llm_config_results.get("llm_elements_found", 0) > 0 or
                llm_config_results.get("config_inputs_found", 0) > 0 or
                llm_config_results.get("has_llm_content", False)
            )
            
            if success:
                self.logger.test_step("LLM配置界面测试通过")
            else:
                self.logger.test_step("LLM配置界面测试失败 - 未找到相关功能")
            
            return success, llm_config_results
            
        except Exception as e:
            return False, {"error": str(e), "error_type": type(e).__name__}