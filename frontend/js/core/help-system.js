/**
 * 帮助和指导系统
 * 提供用户操作指导、帮助提示和快捷键说明
 */
class HelpSystem {
    constructor() {
        this.tooltips = new Map();
        this.guides = new Map();
        this.shortcuts = new Map();
        this.helpModal = null;
        this.currentTour = null;
        
        this.init();
    }
    
    /**
     * 初始化帮助系统
     */
    init() {
        this.setupTooltips();
        this.setupKeyboardShortcuts();
        this.setupHelpModal();
        this.setupGuidedTour();
        this.loadHelpContent();
    }
    
    /**
     * 设置工具提示
     */
    setupTooltips() {
        // 监听带有data-tooltip属性的元素
        document.addEventListener('mouseenter', (event) => {
            const element = event.target.closest('[data-tooltip]');
            if (element) {
                this.showTooltip(element);
            }
        }, true);
        
        document.addEventListener('mouseleave', (event) => {
            const element = event.target.closest('[data-tooltip]');
            if (element) {
                this.hideTooltip(element);
            }
        }, true);
        
        // 触摸设备支持
        document.addEventListener('touchstart', (event) => {
            const element = event.target.closest('[data-tooltip]');
            if (element) {
                this.showTooltip(element);
                // 3秒后自动隐藏
                setTimeout(() => this.hideTooltip(element), 3000);
            }
        });
    }
    
    /**
     * 显示工具提示
     */
    showTooltip(element) {
        const text = element.dataset.tooltip;
        const position = element.dataset.tooltipPosition || 'top';
        const delay = parseInt(element.dataset.tooltipDelay) || 500;
        
        // 防止重复显示
        if (this.tooltips.has(element)) {
            return;
        }
        
        const tooltipId = this.generateId();
        const tooltip = this.createTooltip(tooltipId, text, position);
        
        // 延迟显示
        const timer = setTimeout(() => {
            document.body.appendChild(tooltip);
            this.positionTooltip(tooltip, element, position);
            
            // 添加显示动画
            requestAnimationFrame(() => {
                tooltip.classList.add('show');
            });
            
            this.tooltips.set(element, {
                id: tooltipId,
                element: tooltip,
                timer: null
            });
        }, delay);
        
        this.tooltips.set(element, {
            id: tooltipId,
            element: null,
            timer
        });
    }
    
    /**
     * 创建工具提示元素
     */
    createTooltip(id, text, position) {
        const tooltip = document.createElement('div');
        tooltip.className = `tooltip tooltip-${position}`;
        tooltip.dataset.tooltipId = id;
        tooltip.setAttribute('role', 'tooltip');
        tooltip.innerHTML = `
            <div class="tooltip-content">${text}</div>
            <div class="tooltip-arrow"></div>
        `;
        
        // 添加样式
        tooltip.style.cssText = `
            position: absolute;
            z-index: 1070;
            background: var(--tooltip-bg, #1f2937);
            color: var(--tooltip-color, #f3f4f6);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 14px;
            line-height: 1.4;
            max-width: 250px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            opacity: 0;
            transform: scale(0.9);
            transition: all 0.2s ease;
            pointer-events: none;
        `;
        
        return tooltip;
    }
    
    /**
     * 定位工具提示
     */
    positionTooltip(tooltip, element, position) {
        const rect = element.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
        
        let top, left;
        
        switch (position) {
            case 'top':
                top = rect.top + scrollTop - tooltipRect.height - 8;
                left = rect.left + scrollLeft + (rect.width - tooltipRect.width) / 2;
                break;
            case 'bottom':
                top = rect.bottom + scrollTop + 8;
                left = rect.left + scrollLeft + (rect.width - tooltipRect.width) / 2;
                break;
            case 'left':
                top = rect.top + scrollTop + (rect.height - tooltipRect.height) / 2;
                left = rect.left + scrollLeft - tooltipRect.width - 8;
                break;
            case 'right':
                top = rect.top + scrollTop + (rect.height - tooltipRect.height) / 2;
                left = rect.right + scrollLeft + 8;
                break;
            default:
                top = rect.top + scrollTop - tooltipRect.height - 8;
                left = rect.left + scrollLeft + (rect.width - tooltipRect.width) / 2;
        }
        
        // 边界检查
        const viewport = {
            width: window.innerWidth,
            height: window.innerHeight
        };
        
        if (left < 0) left = 8;
        if (left + tooltipRect.width > viewport.width) {
            left = viewport.width - tooltipRect.width - 8;
        }
        if (top < scrollTop) top = scrollTop + 8;
        if (top + tooltipRect.height > scrollTop + viewport.height) {
            top = scrollTop + viewport.height - tooltipRect.height - 8;
        }
        
        tooltip.style.top = `${top}px`;
        tooltip.style.left = `${left}px`;
    }
    
    /**
     * 隐藏工具提示
     */
    hideTooltip(element) {
        const tooltipData = this.tooltips.get(element);
        if (tooltipData) {
            if (tooltipData.timer) {
                clearTimeout(tooltipData.timer);
            }
            
            if (tooltipData.element) {
                tooltipData.element.classList.remove('show');
                setTimeout(() => {
                    if (tooltipData.element.parentNode) {
                        tooltipData.element.parentNode.removeChild(tooltipData.element);
                    }
                }, 200);
            }
            
            this.tooltips.delete(element);
        }
    }
    
    /**
     * 设置键盘快捷键帮助
     */
    setupKeyboardShortcuts() {
        this.shortcuts.set('general', [
            { key: 'Ctrl + /', description: '显示快捷键帮助' },
            { key: 'Escape', description: '关闭模态框或取消操作' },
            { key: 'Alt + 1', description: '跳转到智能体管理' },
            { key: 'Alt + 2', description: '跳转到任务管理' },
            { key: 'Alt + 3', description: '跳转到配置管理' }
        ]);
        
        this.shortcuts.set('agent-management', [
            { key: 'Ctrl + N', description: '创建新智能体配置' },
            { key: 'Ctrl + E', description: '编辑选中的智能体' },
            { key: 'Delete', description: '删除选中的智能体' },
            { key: 'F5', description: '刷新智能体状态' }
        ]);
        
        this.shortcuts.set('task-creation', [
            { key: 'Ctrl + Enter', description: '提交任务' },
            { key: 'Ctrl + S', description: '保存草稿' },
            { key: 'Tab', description: '在表单字段间切换' },
            { key: 'Shift + Tab', description: '反向切换表单字段' }
        ]);
        
        this.shortcuts.set('chat', [
            { key: 'Enter', description: '发送消息' },
            { key: 'Shift + Enter', description: '换行' },
            { key: '↑', description: '编辑上一条消息' },
            { key: 'Ctrl + K', description: '清空对话' }
        ]);
    }
    
    /**
     * 设置帮助模态框
     */
    setupHelpModal() {
        // 监听快捷键
        document.addEventListener('keydown', (event) => {
            if (event.ctrlKey && event.key === '/') {
                event.preventDefault();
                this.showHelpModal();
            }
        });
        
        // 创建帮助按钮
        this.createHelpButton();
    }
    
    /**
     * 创建帮助按钮
     */
    createHelpButton() {
        const helpButton = document.createElement('button');
        helpButton.className = 'help-button';
        helpButton.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75l-.9.92C13.45 12.9 13 13.5 13 15h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H8c0-2.21 1.79-4 4-4s4 1.79 4 4c0 .88-.36 1.68-.93 2.25z"/>
            </svg>
        `;
        helpButton.title = '帮助 (Ctrl + /)';
        helpButton.setAttribute('data-tooltip', '点击查看帮助信息');
        
        helpButton.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: var(--primary-color, #3b82f6);
            color: white;
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            z-index: 1000;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        
        helpButton.addEventListener('click', () => {
            this.showHelpModal();
        });
        
        helpButton.addEventListener('mouseenter', () => {
            helpButton.style.transform = 'scale(1.1)';
        });
        
        helpButton.addEventListener('mouseleave', () => {
            helpButton.style.transform = 'scale(1)';
        });
        
        document.body.appendChild(helpButton);
    }
    
    /**
     * 显示帮助模态框
     */
    showHelpModal() {
        if (this.helpModal) {
            return; // 已经显示
        }
        
        this.helpModal = this.createHelpModal();
        document.body.appendChild(this.helpModal);
        
        // 焦点管理
        const firstTab = this.helpModal.querySelector('.help-tab');
        if (firstTab) {
            firstTab.focus();
        }
        
        // 显示动画
        requestAnimationFrame(() => {
            this.helpModal.classList.add('show');
        });
    }
    
    /**
     * 创建帮助模态框
     */
    createHelpModal() {
        const modal = document.createElement('div');
        modal.className = 'help-modal';
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-modal', 'true');
        modal.setAttribute('aria-labelledby', 'help-title');
        
        modal.innerHTML = `
            <div class="help-content">
                <div class="help-header">
                    <h2 id="help-title">帮助中心</h2>
                    <button class="help-close" aria-label="关闭帮助">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                        </svg>
                    </button>
                </div>
                
                <div class="help-tabs">
                    <button class="help-tab active" data-tab="shortcuts">快捷键</button>
                    <button class="help-tab" data-tab="features">功能说明</button>
                    <button class="help-tab" data-tab="faq">常见问题</button>
                </div>
                
                <div class="help-body">
                    <div class="help-tab-content active" data-content="shortcuts">
                        ${this.createShortcutsContent()}
                    </div>
                    <div class="help-tab-content" data-content="features">
                        ${this.createFeaturesContent()}
                    </div>
                    <div class="help-tab-content" data-content="faq">
                        ${this.createFAQContent()}
                    </div>
                </div>
            </div>
        `;
        
        // 添加样式
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.75);
            z-index: 1080;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: opacity 0.3s ease;
            padding: 20px;
        `;
        
        // 绑定事件
        this.bindHelpModalEvents(modal);
        
        return modal;
    }
    
    /**
     * 绑定帮助模态框事件
     */
    bindHelpModalEvents(modal) {
        // 关闭按钮
        const closeBtn = modal.querySelector('.help-close');
        closeBtn.addEventListener('click', () => {
            this.hideHelpModal();
        });
        
        // 点击背景关闭
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                this.hideHelpModal();
            }
        });
        
        // ESC键关闭
        const handleKeydown = (event) => {
            if (event.key === 'Escape') {
                this.hideHelpModal();
                document.removeEventListener('keydown', handleKeydown);
            }
        };
        document.addEventListener('keydown', handleKeydown);
        
        // 标签页切换
        const tabs = modal.querySelectorAll('.help-tab');
        const contents = modal.querySelectorAll('.help-tab-content');
        
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const targetTab = tab.dataset.tab;
                
                // 更新标签页状态
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                
                // 更新内容显示
                contents.forEach(content => {
                    content.classList.remove('active');
                    if (content.dataset.content === targetTab) {
                        content.classList.add('active');
                    }
                });
            });
        });
    }
    
    /**
     * 创建快捷键内容
     */
    createShortcutsContent() {
        let html = '';
        
        this.shortcuts.forEach((shortcuts, category) => {
            const categoryName = this.getCategoryName(category);
            html += `
                <div class="shortcut-category">
                    <h3>${categoryName}</h3>
                    <div class="shortcut-list">
                        ${shortcuts.map(shortcut => `
                            <div class="shortcut-item">
                                <kbd class="shortcut-key">${shortcut.key}</kbd>
                                <span class="shortcut-desc">${shortcut.description}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        });
        
        return html;
    }
    
    /**
     * 创建功能说明内容
     */
    createFeaturesContent() {
        return `
            <div class="feature-section">
                <h3>智能体管理</h3>
                <ul>
                    <li>查看所有智能体的实时状态和统计信息</li>
                    <li>配置智能体参数和约束条件</li>
                    <li>监控智能体的执行历史和日志</li>
                    <li>支持智能体的启动、停止和重启操作</li>
                </ul>
            </div>
            
            <div class="feature-section">
                <h3>大模型配置</h3>
                <ul>
                    <li>支持多种大模型提供商（SiliconFlow、OpenAI等）</li>
                    <li>安全的API密钥管理和加密存储</li>
                    <li>配置测试和连接状态验证</li>
                    <li>使用统计和性能监控</li>
                </ul>
            </div>
            
            <div class="feature-section">
                <h3>任务创建</h3>
                <ul>
                    <li>智能引导创建：通过元智能体对话获得任务规划建议</li>
                    <li>直接创建：快速填写任务信息创建任务</li>
                    <li>任务拆解：将复杂任务自动分解为子任务</li>
                    <li>任务依赖关系管理和优先级设置</li>
                </ul>
            </div>
        `;
    }
    
    /**
     * 创建FAQ内容
     */
    createFAQContent() {
        return `
            <div class="faq-item">
                <h4>如何添加新的大模型配置？</h4>
                <p>在智能体管理页面点击"添加配置"按钮，选择提供商类型，填写API密钥和相关参数，然后点击"测试连接"验证配置是否正确。</p>
            </div>
            
            <div class="faq-item">
                <h4>智能体状态显示为错误怎么办？</h4>
                <p>首先检查大模型配置是否正确，然后查看智能体的详细日志信息。如果问题持续存在，可以尝试重启智能体或联系技术支持。</p>
            </div>
            
            <div class="faq-item">
                <h4>如何使用任务拆解功能？</h4>
                <p>在元智能体引导创建过程中，当任务复杂度达到阈值时会自动显示"任务拆解"按钮。点击后系统会将复杂任务分解为多个子任务，您可以编辑和确认拆解结果。</p>
            </div>
            
            <div class="faq-item">
                <h4>系统支持哪些浏览器？</h4>
                <p>推荐使用Chrome、Firefox、Safari或Edge的最新版本。系统支持响应式设计，可以在桌面和移动设备上正常使用。</p>
            </div>
        `;
    }
    
    /**
     * 获取分类名称
     */
    getCategoryName(category) {
        const names = {
            'general': '通用快捷键',
            'agent-management': '智能体管理',
            'task-creation': '任务创建',
            'chat': '对话交互'
        };
        
        return names[category] || category;
    }
    
    /**
     * 隐藏帮助模态框
     */
    hideHelpModal() {
        if (this.helpModal) {
            this.helpModal.classList.remove('show');
            setTimeout(() => {
                if (this.helpModal.parentNode) {
                    this.helpModal.parentNode.removeChild(this.helpModal);
                }
                this.helpModal = null;
            }, 300);
        }
    }
    
    /**
     * 设置引导教程
     */
    setupGuidedTour() {
        // 检查是否是首次访问
        if (!localStorage.getItem('tour_completed')) {
            setTimeout(() => {
                this.startGuidedTour();
            }, 2000);
        }
    }
    
    /**
     * 开始引导教程
     */
    startGuidedTour() {
        const tourSteps = [
            {
                target: '.agent-management-section',
                title: '欢迎使用智能体管理系统',
                content: '这里是智能体管理区域，您可以查看和管理所有智能体的状态。',
                position: 'bottom'
            },
            {
                target: '.llm-config-section',
                title: '大模型配置',
                content: '在这里配置和管理大语言模型的参数和API密钥。',
                position: 'top'
            },
            {
                target: '.task-creation-area',
                title: '任务创建',
                content: '您可以选择智能引导创建或直接创建任务。',
                position: 'left'
            }
        ];
        
        this.currentTour = new GuidedTour(tourSteps, {
            onComplete: () => {
                localStorage.setItem('tour_completed', 'true');
                this.currentTour = null;
            },
            onSkip: () => {
                localStorage.setItem('tour_completed', 'true');
                this.currentTour = null;
            }
        });
        
        this.currentTour.start();
    }
    
    /**
     * 加载帮助内容
     */
    loadHelpContent() {
        // 从服务器或本地文件加载帮助内容
        // 这里可以实现动态加载帮助文档
    }
    
    /**
     * 生成唯一ID
     */
    generateId() {
        return Math.random().toString(36).substr(2, 9);
    }
    
    /**
     * 销毁帮助系统
     */
    destroy() {
        this.tooltips.clear();
        this.guides.clear();
        this.shortcuts.clear();
        
        if (this.helpModal) {
            this.hideHelpModal();
        }
        
        if (this.currentTour) {
            this.currentTour.stop();
        }
    }
}

/**
 * 引导教程类
 */
class GuidedTour {
    constructor(steps, options = {}) {
        this.steps = steps;
        this.currentStep = 0;
        this.options = {
            onComplete: null,
            onSkip: null,
            ...options
        };
        this.overlay = null;
        this.tooltip = null;
    }
    
    start() {
        this.createOverlay();
        this.showStep(0);
    }
    
    createOverlay() {
        this.overlay = document.createElement('div');
        this.overlay.className = 'tour-overlay';
        this.overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1090;
            pointer-events: none;
        `;
        
        document.body.appendChild(this.overlay);
    }
    
    showStep(stepIndex) {
        if (stepIndex >= this.steps.length) {
            this.complete();
            return;
        }
        
        const step = this.steps[stepIndex];
        const target = document.querySelector(step.target);
        
        if (!target) {
            this.next();
            return;
        }
        
        this.highlightElement(target);
        this.showTooltip(target, step);
        this.currentStep = stepIndex;
    }
    
    highlightElement(element) {
        // 移除之前的高亮
        const prevHighlight = document.querySelector('.tour-highlight');
        if (prevHighlight) {
            prevHighlight.classList.remove('tour-highlight');
        }
        
        // 添加高亮效果
        element.classList.add('tour-highlight');
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    
    showTooltip(target, step) {
        if (this.tooltip) {
            this.tooltip.remove();
        }
        
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'tour-tooltip';
        this.tooltip.innerHTML = `
            <div class="tour-content">
                <h4>${step.title}</h4>
                <p>${step.content}</p>
                <div class="tour-actions">
                    <button class="tour-skip">跳过教程</button>
                    <div class="tour-navigation">
                        <span class="tour-progress">${this.currentStep + 1} / ${this.steps.length}</span>
                        <button class="tour-next">下一步</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(this.tooltip);
        this.positionTooltip(target, step.position);
        
        // 绑定事件
        this.tooltip.querySelector('.tour-skip').addEventListener('click', () => {
            this.skip();
        });
        
        this.tooltip.querySelector('.tour-next').addEventListener('click', () => {
            this.next();
        });
    }
    
    positionTooltip(target, position) {
        const rect = target.getBoundingClientRect();
        const tooltip = this.tooltip;
        
        // 基本样式
        tooltip.style.cssText = `
            position: fixed;
            z-index: 1095;
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            max-width: 300px;
        `;
        
        // 根据位置调整
        switch (position) {
            case 'top':
                tooltip.style.bottom = `${window.innerHeight - rect.top + 10}px`;
                tooltip.style.left = `${rect.left + rect.width / 2}px`;
                tooltip.style.transform = 'translateX(-50%)';
                break;
            case 'bottom':
                tooltip.style.top = `${rect.bottom + 10}px`;
                tooltip.style.left = `${rect.left + rect.width / 2}px`;
                tooltip.style.transform = 'translateX(-50%)';
                break;
            case 'left':
                tooltip.style.top = `${rect.top + rect.height / 2}px`;
                tooltip.style.right = `${window.innerWidth - rect.left + 10}px`;
                tooltip.style.transform = 'translateY(-50%)';
                break;
            case 'right':
                tooltip.style.top = `${rect.top + rect.height / 2}px`;
                tooltip.style.left = `${rect.right + 10}px`;
                tooltip.style.transform = 'translateY(-50%)';
                break;
        }
    }
    
    next() {
        this.showStep(this.currentStep + 1);
    }
    
    skip() {
        this.cleanup();
        if (this.options.onSkip) {
            this.options.onSkip();
        }
    }
    
    complete() {
        this.cleanup();
        if (this.options.onComplete) {
            this.options.onComplete();
        }
    }
    
    stop() {
        this.cleanup();
    }
    
    cleanup() {
        if (this.overlay) {
            this.overlay.remove();
            this.overlay = null;
        }
        
        if (this.tooltip) {
            this.tooltip.remove();
            this.tooltip = null;
        }
        
        // 移除高亮
        const highlight = document.querySelector('.tour-highlight');
        if (highlight) {
            highlight.classList.remove('tour-highlight');
        }
    }
}

// 创建全局实例
window.helpSystem = new HelpSystem();

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { HelpSystem, GuidedTour };
}