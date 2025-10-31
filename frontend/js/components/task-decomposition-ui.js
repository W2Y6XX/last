/**
 * 任务拆解用户界面组件
 * 负责复杂度分析显示、拆解按钮控制和拆解结果展示
 */
class TaskDecompositionUI {
    constructor() {
        this.complexityThreshold = 0.7;
        this.currentComplexity = 0;
        this.canDecompose = false;
        this.decompositionResult = null;
        this.isDecomposing = false;
        this.editMode = false;
        
        // 绑定事件处理器
        this.handleComplexityUpdate = this.handleComplexityUpdate.bind(this);
        this.handleDecompositionComplete = this.handleDecompositionComplete.bind(this);
        
        // 初始化UI组件
        this.initializeComponents();
    }
    
    /**
     * 初始化UI组件
     */
    initializeComponents() {
        this.createComplexityIndicator();
        this.createDecomposeButton();
        this.createDecompositionResultContainer();
        this.bindEvents();
    }
    
    /**
     * 创建复杂度指示器
     */
    createComplexityIndicator() {
        const indicatorHTML = `
            <div id="complexityIndicator" class="complexity-indicator glass-morphism rounded-lg p-4 mb-4" style="display: none;">
                <div class="flex items-center justify-between mb-3">
                    <h4 class="text-sm font-semibold text-blue-100">任务复杂度分析</h4>
                    <button id="complexitySettings" class="text-xs text-purple-300 hover:text-purple-200" onclick="showComplexitySettings()">
                        <i class="fas fa-cog"></i> 设置
                    </button>
                </div>
                
                <div class="complexity-score-container mb-3">
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-xs text-blue-200">复杂度评分</span>
                        <span id="complexityScore" class="text-sm font-bold text-white">0%</span>
                    </div>
                    
                    <div class="complexity-progress-bar bg-gray-700 rounded-full h-2 relative overflow-hidden">
                        <div id="complexityProgress" class="complexity-progress h-full rounded-full transition-all duration-500" style="width: 0%; background: #10b981;"></div>
                        <div id="complexityThreshold" class="absolute top-0 h-full w-0.5 bg-white opacity-75" style="left: 70%;"></div>
                    </div>
                    
                    <div class="flex justify-between text-xs text-gray-400 mt-1">
                        <span>简单</span>
                        <span id="thresholdLabel">拆解阈值 (70%)</span>
                        <span>复杂</span>
                    </div>
                </div>
                
                <div id="complexityDetails" class="complexity-details">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center">
                            <span id="complexityLevel" class="complexity-level px-2 py-1 rounded text-xs font-medium">简单</span>
                            <span id="complexityRecommendation" class="text-xs text-gray-300 ml-2">可以直接创建</span>
                        </div>
                        <div id="complexityFactors" class="text-xs text-gray-400">
                            <i class="fas fa-info-circle cursor-help" title="点击查看复杂度因素"></i>
                        </div>
                    </div>
                </div>
                
                <div id="complexityFactorsDetail" class="complexity-factors-detail mt-3 p-3 bg-gray-800 rounded-lg" style="display: none;">
                    <h5 class="text-xs font-semibold text-blue-200 mb-2">复杂度影响因素:</h5>
                    <div id="factorsList" class="space-y-1 text-xs text-gray-300">
                        <!-- 动态填充因素列表 -->
                    </div>
                </div>
            </div>
        `;
        
        // 将指示器添加到对话界面
        this.insertComplexityIndicator(indicatorHTML);
    }
    
    /**
     * 创建拆解按钮
     */
    createDecomposeButton() {
        const buttonHTML = `
            <button id="decomposeButton" class="decompose-btn w-full mt-3 px-4 py-2 rounded-lg transition-all duration-300" 
                    style="display: none;" onclick="requestTaskDecomposition()">
                <div class="flex items-center justify-center">
                    <i id="decomposeIcon" class="fas fa-puzzle-piece mr-2"></i>
                    <span id="decomposeText">任务拆解</span>
                </div>
                <div id="decomposeSubtext" class="text-xs opacity-75 mt-1">
                    将复杂任务分解为多个子任务
                </div>
            </button>
        `;
        
        // 将按钮添加到对话输入区域
        this.insertDecomposeButton(buttonHTML);
    }
    
    /**
     * 创建拆解结果容器
     */
    createDecompositionResultContainer() {
        const containerHTML = `
            <div id="decompositionResultContainer" class="decomposition-result-container" style="display: none;">
                <div class="glass-morphism rounded-xl p-6 mt-4">
                    <div class="decomposition-header flex items-center justify-between mb-4">
                        <h4 class="text-lg font-semibold text-blue-100 flex items-center">
                            <i class="fas fa-sitemap mr-2 text-purple-300"></i>
                            任务拆解结果
                        </h4>
                        <div class="decomposition-actions flex items-center space-x-2">
                            <button id="editDecompositionBtn" class="text-xs px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded transition-all" onclick="toggleEditMode()">
                                <i class="fas fa-edit mr-1"></i>编辑
                            </button>
                            <button id="regenerateBtn" class="text-xs px-3 py-1 bg-purple-600 hover:bg-purple-700 rounded transition-all" onclick="regenerateDecomposition()">
                                <i class="fas fa-redo mr-1"></i>重新拆解
                            </button>
                        </div>
                    </div>
                    
                    <div id="decompositionStats" class="decomposition-stats grid grid-cols-3 gap-4 mb-4">
                        <!-- 统计信息 -->
                    </div>
                    
                    <div id="mainTaskContainer" class="main-task-container mb-4">
                        <!-- 主任务 -->
                    </div>
                    
                    <div id="subtasksContainer" class="subtasks-container mb-4">
                        <!-- 子任务列表 -->
                    </div>
                    
                    <div id="dependenciesContainer" class="dependencies-container mb-4" style="display: none;">
                        <!-- 依赖关系图 -->
                    </div>
                    
                    <div class="decomposition-footer flex justify-end space-x-3">
                        <button id="cancelDecompositionBtn" class="px-4 py-2 rounded-lg hover:bg-white hover:bg-opacity-10 transition-all" onclick="cancelDecomposition()">
                            取消
                        </button>
                        <button id="confirmDecompositionBtn" class="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg transition-all text-white" onclick="confirmDecomposition()">
                            <i class="fas fa-check mr-2"></i>确认创建
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // 将容器添加到对话界面
        this.insertDecompositionContainer(containerHTML);
    }
    
    /**
     * 绑定事件
     */
    bindEvents() {
        // 监听复杂度因素详情切换
        document.addEventListener('click', (e) => {
            if (e.target.closest('#complexityFactors')) {
                this.toggleComplexityFactors();
            }
        });
        
        // 监听阈值设置变化
        document.addEventListener('change', (e) => {
            if (e.target.id === 'thresholdSlider') {
                this.updateThreshold(parseFloat(e.target.value));
            }
        });
    }
    
    /**
     * 插入复杂度指示器到对话界面
     */
    insertComplexityIndicator(html) {
        // 查找对话输入区域
        const chatInput = document.querySelector('.chat-input');
        if (chatInput) {
            chatInput.insertAdjacentHTML('beforebegin', html);
        } else {
            // 如果找不到对话输入区域，添加到元智能体对话容器
            const chatContainer = document.querySelector('.meta-agent-chat');
            if (chatContainer) {
                const messagesContainer = chatContainer.querySelector('.chat-messages');
                if (messagesContainer) {
                    messagesContainer.insertAdjacentHTML('afterend', html);
                }
            }
        }
    }
    
    /**
     * 插入拆解按钮到对话输入区域
     */
    insertDecomposeButton(html) {
        const inputActions = document.querySelector('.input-actions');
        if (inputActions) {
            inputActions.insertAdjacentHTML('beforeend', html);
        } else {
            // 如果找不到输入操作区域，添加到对话输入区域
            const chatInput = document.querySelector('.chat-input');
            if (chatInput) {
                chatInput.insertAdjacentHTML('beforeend', html);
            }
        }
    }
    
    /**
     * 插入拆解结果容器
     */
    insertDecompositionContainer(html) {
        const chatContainer = document.querySelector('.meta-agent-chat');
        if (chatContainer) {
            chatContainer.insertAdjacentHTML('afterend', html);
        } else {
            // 如果找不到对话容器，添加到页面主要内容区域
            const mainContent = document.querySelector('.max-w-2xl');
            if (mainContent) {
                mainContent.insertAdjacentHTML('beforeend', html);
            }
        }
    }
    
    /**
     * 更新复杂度显示
     * @param {Object} complexityData 复杂度数据
     */
    updateComplexityDisplay(complexityData) {
        this.currentComplexity = complexityData.complexity || 0;
        this.canDecompose = complexityData.canDecompose || false;
        
        const indicator = document.getElementById('complexityIndicator');
        if (!indicator) return;
        
        // 显示指示器
        indicator.style.display = 'block';
        
        // 更新评分
        const scoreElement = document.getElementById('complexityScore');
        const progressElement = document.getElementById('complexityProgress');
        const levelElement = document.getElementById('complexityLevel');
        const recommendationElement = document.getElementById('complexityRecommendation');
        
        if (scoreElement) {
            scoreElement.textContent = Math.round(this.currentComplexity * 100) + '%';
        }
        
        if (progressElement) {
            const percentage = this.currentComplexity * 100;
            progressElement.style.width = percentage + '%';
            progressElement.style.background = this.getComplexityColor(this.currentComplexity);
        }
        
        if (levelElement) {
            const level = this.getComplexityLevel(this.currentComplexity);
            levelElement.textContent = level;
            levelElement.className = `complexity-level px-2 py-1 rounded text-xs font-medium ${this.getComplexityLevelClass(this.currentComplexity)}`;
        }
        
        if (recommendationElement) {
            recommendationElement.textContent = this.getComplexityRecommendation(this.currentComplexity);
        }
        
        // 更新因素列表
        if (complexityData.factors) {
            this.updateComplexityFactors(complexityData.factors);
        }
        
        // 更新拆解按钮状态
        this.updateDecomposeButtonState();
    }
    
    /**
     * 更新复杂度因素列表
     */
    updateComplexityFactors(factors) {
        const factorsList = document.getElementById('factorsList');
        if (!factorsList || !factors || factors.length === 0) return;
        
        factorsList.innerHTML = factors.map(factor => `
            <div class="flex items-center justify-between">
                <span>${factor.name}</span>
                <span class="text-purple-300">${factor.impact}</span>
            </div>
        `).join('');
    }
    
    /**
     * 更新拆解按钮状态
     */
    updateDecomposeButtonState() {
        const button = document.getElementById('decomposeButton');
        if (!button) return;
        
        if (this.canDecompose && !this.isDecomposing) {
            button.style.display = 'block';
            button.className = 'decompose-btn w-full mt-3 px-4 py-2 rounded-lg transition-all duration-300 bg-purple-600 hover:bg-purple-700 text-white';
            button.disabled = false;
            
            const icon = document.getElementById('decomposeIcon');
            const text = document.getElementById('decomposeText');
            const subtext = document.getElementById('decomposeSubtext');
            
            if (icon) icon.className = 'fas fa-puzzle-piece mr-2';
            if (text) text.textContent = '任务拆解';
            if (subtext) subtext.textContent = '将复杂任务分解为多个子任务';
            
        } else if (this.isDecomposing) {
            button.style.display = 'block';
            button.className = 'decompose-btn w-full mt-3 px-4 py-2 rounded-lg transition-all duration-300 bg-gray-600 text-white';
            button.disabled = true;
            
            const icon = document.getElementById('decomposeIcon');
            const text = document.getElementById('decomposeText');
            const subtext = document.getElementById('decomposeSubtext');
            
            if (icon) icon.className = 'fas fa-spinner fa-spin mr-2';
            if (text) text.textContent = '正在拆解...';
            if (subtext) subtext.textContent = '请稍候，正在分析任务结构';
            
        } else {
            button.style.display = 'none';
        }
    }
    
    /**
     * 显示拆解结果
     * @param {Object} result 拆解结果
     */
    showDecompositionResult(result) {
        this.decompositionResult = result;
        this.isDecomposing = false;
        
        const container = document.getElementById('decompositionResultContainer');
        if (!container) return;
        
        // 显示容器
        container.style.display = 'block';
        
        // 更新统计信息
        this.updateDecompositionStats(result);
        
        // 显示主任务
        this.displayMainTask(result.mainTask);
        
        // 显示子任务
        this.displaySubtasks(result.subtasks);
        
        // 显示依赖关系（如果有）
        if (result.dependencies && result.dependencies.length > 0) {
            this.displayDependencies(result.dependencies);
        }
        
        // 更新按钮状态
        this.updateDecomposeButtonState();
        
        // 滚动到结果区域
        container.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    /**
     * 更新拆解统计信息
     */
    updateDecompositionStats(result) {
        const statsContainer = document.getElementById('decompositionStats');
        if (!statsContainer) return;
        
        const subtaskCount = result.subtasks ? result.subtasks.length : 0;
        const totalTime = result.estimatedTotalTime || 0;
        const complexity = result.complexity || this.currentComplexity;
        
        statsContainer.innerHTML = `
            <div class="stat-item text-center p-3 bg-gray-800 rounded-lg">
                <div class="text-lg font-bold text-blue-100">${subtaskCount}</div>
                <div class="text-xs text-gray-400">子任务数量</div>
            </div>
            <div class="stat-item text-center p-3 bg-gray-800 rounded-lg">
                <div class="text-lg font-bold text-blue-100">${totalTime}h</div>
                <div class="text-xs text-gray-400">预计总时长</div>
            </div>
            <div class="stat-item text-center p-3 bg-gray-800 rounded-lg">
                <div class="text-lg font-bold text-blue-100">${Math.round(complexity * 100)}%</div>
                <div class="text-xs text-gray-400">复杂度评分</div>
            </div>
        `;
    }
    
    /**
     * 显示主任务
     */
    displayMainTask(mainTask) {
        const container = document.getElementById('mainTaskContainer');
        if (!container || !mainTask) return;
        
        container.innerHTML = `
            <div class="task-item main glass-morphism rounded-lg p-4">
                <div class="task-header flex items-center justify-between mb-3">
                    <h5 class="text-lg font-semibold text-blue-100 flex items-center">
                        <i class="fas fa-star mr-2 text-yellow-400"></i>
                        主任务
                    </h5>
                    <span class="task-priority priority-${mainTask.priority || 'medium'}">${this.getPriorityText(mainTask.priority)}</span>
                </div>
                <div class="task-content">
                    <h6 class="text-md font-medium text-white mb-2">${mainTask.title || mainTask.name || '未命名任务'}</h6>
                    <p class="text-sm text-gray-300 mb-3">${mainTask.description || '暂无描述'}</p>
                    <div class="task-meta flex items-center space-x-4 text-xs text-gray-400">
                        ${mainTask.estimatedTime ? `<span><i class="far fa-clock mr-1"></i>${mainTask.estimatedTime}h</span>` : ''}
                        ${mainTask.deadline ? `<span><i class="far fa-calendar mr-1"></i>${mainTask.deadline}</span>` : ''}
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * 显示子任务列表
     */
    displaySubtasks(subtasks) {
        const container = document.getElementById('subtasksContainer');
        if (!container || !subtasks || subtasks.length === 0) return;
        
        const subtasksHTML = `
            <div class="subtasks-header mb-3">
                <h5 class="text-md font-semibold text-blue-100 flex items-center">
                    <i class="fas fa-list mr-2 text-blue-400"></i>
                    子任务列表 (${subtasks.length})
                </h5>
            </div>
            <div class="subtasks-list space-y-3">
                ${subtasks.map((subtask, index) => this.createSubtaskHTML(subtask, index)).join('')}
            </div>
        `;
        
        container.innerHTML = subtasksHTML;
    }
    
    /**
     * 创建子任务HTML
     */
    createSubtaskHTML(subtask, index) {
        return `
            <div class="task-item subtask glass-morphism rounded-lg p-4" data-task-index="${index}">
                <div class="task-header flex items-center justify-between mb-2">
                    <div class="flex items-center">
                        <span class="task-number w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center text-xs font-bold mr-3">${index + 1}</span>
                        <h6 class="text-md font-medium text-white">${subtask.title || subtask.name || '未命名子任务'}</h6>
                    </div>
                    <div class="task-actions flex items-center space-x-2">
                        <span class="task-priority priority-${subtask.priority || 'medium'}">${this.getPriorityText(subtask.priority)}</span>
                        ${this.editMode ? `
                            <button class="edit-task-btn text-xs px-2 py-1 bg-blue-600 hover:bg-blue-700 rounded" onclick="editSubtask(${index})">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="delete-task-btn text-xs px-2 py-1 bg-red-600 hover:bg-red-700 rounded" onclick="deleteSubtask(${index})">
                                <i class="fas fa-trash"></i>
                            </button>
                        ` : ''}
                    </div>
                </div>
                <div class="task-content">
                    <p class="text-sm text-gray-300 mb-2">${subtask.description || '暂无描述'}</p>
                    <div class="task-meta flex items-center space-x-4 text-xs text-gray-400">
                        ${subtask.estimatedTime ? `<span><i class="far fa-clock mr-1"></i>${subtask.estimatedTime}h</span>` : ''}
                        ${subtask.dependencies && subtask.dependencies.length > 0 ? `<span><i class="fas fa-link mr-1"></i>依赖: ${subtask.dependencies.join(', ')}</span>` : ''}
                    </div>
                </div>
                ${this.editMode ? this.createEditForm(subtask, index) : ''}
            </div>
        `;
    }
    
    /**
     * 创建编辑表单
     */
    createEditForm(subtask, index) {
        return `
            <div class="task-edit-form mt-3 p-3 bg-gray-800 rounded-lg" style="display: none;">
                <div class="space-y-3">
                    <input type="text" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white" 
                           placeholder="任务标题" value="${subtask.title || subtask.name || ''}" data-field="title">
                    <textarea class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white" 
                              placeholder="任务描述" rows="3" data-field="description">${subtask.description || ''}</textarea>
                    <div class="flex space-x-3">
                        <select class="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white" data-field="priority">
                            <option value="low" ${subtask.priority === 'low' ? 'selected' : ''}>低优先级</option>
                            <option value="medium" ${subtask.priority === 'medium' ? 'selected' : ''}>中优先级</option>
                            <option value="high" ${subtask.priority === 'high' ? 'selected' : ''}>高优先级</option>
                        </select>
                        <input type="number" class="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white" 
                               placeholder="预计时长(小时)" value="${subtask.estimatedTime || ''}" data-field="estimatedTime">
                    </div>
                    <div class="flex justify-end space-x-2">
                        <button class="px-3 py-1 bg-gray-600 hover:bg-gray-700 rounded text-xs" onclick="cancelEditSubtask(${index})">取消</button>
                        <button class="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-xs" onclick="saveEditSubtask(${index})">保存</button>
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * 显示依赖关系
     */
    displayDependencies(dependencies) {
        const container = document.getElementById('dependenciesContainer');
        if (!container || !dependencies || dependencies.length === 0) return;
        
        container.style.display = 'block';
        container.innerHTML = `
            <div class="dependencies-header mb-3">
                <h5 class="text-md font-semibold text-blue-100 flex items-center">
                    <i class="fas fa-project-diagram mr-2 text-green-400"></i>
                    任务依赖关系
                </h5>
            </div>
            <div class="dependencies-graph bg-gray-800 rounded-lg p-4">
                ${dependencies.map(dep => `
                    <div class="dependency-item flex items-center justify-between py-2 border-b border-gray-700 last:border-b-0">
                        <span class="text-sm text-gray-300">${dep.from}</span>
                        <i class="fas fa-arrow-right text-purple-400 mx-3"></i>
                        <span class="text-sm text-gray-300">${dep.to}</span>
                        <span class="text-xs text-gray-500 ml-3">${dep.type || '依赖'}</span>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    /**
     * 获取复杂度等级
     */
    getComplexityLevel(complexity) {
        if (complexity < 0.3) return '简单';
        if (complexity < 0.5) return '中等';
        if (complexity < 0.7) return '复杂';
        return '非常复杂';
    }
    
    /**
     * 获取复杂度颜色
     */
    getComplexityColor(complexity) {
        if (complexity < 0.3) return '#10b981';
        if (complexity < 0.5) return '#f59e0b';
        if (complexity < 0.7) return '#f97316';
        return '#ef4444';
    }
    
    /**
     * 获取复杂度等级样式类
     */
    getComplexityLevelClass(complexity) {
        if (complexity < 0.3) return 'bg-green-600 text-white';
        if (complexity < 0.5) return 'bg-yellow-600 text-white';
        if (complexity < 0.7) return 'bg-orange-600 text-white';
        return 'bg-red-600 text-white';
    }
    
    /**
     * 获取复杂度建议
     */
    getComplexityRecommendation(complexity) {
        if (complexity < this.complexityThreshold) {
            return '任务复杂度较低，可以直接创建';
        } else {
            return '任务复杂度较高，建议进行任务拆解';
        }
    }
    
    /**
     * 获取优先级文本
     */
    getPriorityText(priority) {
        const priorityMap = {
            'low': '低',
            'medium': '中',
            'high': '高',
            'urgent': '紧急'
        };
        return priorityMap[priority] || '中';
    }
    
    /**
     * 切换复杂度因素详情显示
     */
    toggleComplexityFactors() {
        const detail = document.getElementById('complexityFactorsDetail');
        if (detail) {
            detail.style.display = detail.style.display === 'none' ? 'block' : 'none';
        }
    }
    
    /**
     * 更新阈值
     */
    updateThreshold(newThreshold) {
        this.complexityThreshold = newThreshold;
        this.canDecompose = this.currentComplexity >= this.complexityThreshold;
        
        // 更新阈值显示
        const thresholdElement = document.getElementById('complexityThreshold');
        const thresholdLabel = document.getElementById('thresholdLabel');
        
        if (thresholdElement) {
            thresholdElement.style.left = (newThreshold * 100) + '%';
        }
        
        if (thresholdLabel) {
            thresholdLabel.textContent = `拆解阈值 (${Math.round(newThreshold * 100)}%)`;
        }
        
        // 更新按钮状态
        this.updateDecomposeButtonState();
        
        // 更新建议
        const recommendationElement = document.getElementById('complexityRecommendation');
        if (recommendationElement) {
            recommendationElement.textContent = this.getComplexityRecommendation(this.currentComplexity);
        }
    }
    
    /**
     * 开始拆解
     */
    startDecomposition() {
        this.isDecomposing = true;
        this.updateDecomposeButtonState();
    }
    
    /**
     * 隐藏拆解结果
     */
    hideDecompositionResult() {
        const container = document.getElementById('decompositionResultContainer');
        if (container) {
            container.style.display = 'none';
        }
        this.decompositionResult = null;
    }
    
    /**
     * 切换编辑模式
     */
    toggleEditMode() {
        this.editMode = !this.editMode;
        
        const editBtn = document.getElementById('editDecompositionBtn');
        if (editBtn) {
            if (this.editMode) {
                editBtn.innerHTML = '<i class="fas fa-save mr-1"></i>保存';
                editBtn.className = 'text-xs px-3 py-1 bg-green-600 hover:bg-green-700 rounded transition-all';
            } else {
                editBtn.innerHTML = '<i class="fas fa-edit mr-1"></i>编辑';
                editBtn.className = 'text-xs px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded transition-all';
            }
        }
        
        // 重新渲染子任务列表以显示/隐藏编辑控件
        if (this.decompositionResult && this.decompositionResult.subtasks) {
            this.displaySubtasks(this.decompositionResult.subtasks);
        }
    }
    
    /**
     * 处理复杂度更新事件
     */
    handleComplexityUpdate(eventType, data) {
        if (eventType === 'complexity_analyzed') {
            this.updateComplexityDisplay(data);
        }
    }
    
    /**
     * 处理拆解完成事件
     */
    handleDecompositionComplete(eventType, data) {
        if (eventType === 'task_decomposed') {
            this.showDecompositionResult(data.decompositionResult);
        }
    }
    
    /**
     * 重置UI状态
     */
    reset() {
        this.currentComplexity = 0;
        this.canDecompose = false;
        this.decompositionResult = null;
        this.isDecomposing = false;
        this.editMode = false;
        
        // 隐藏所有UI元素
        const indicator = document.getElementById('complexityIndicator');
        const button = document.getElementById('decomposeButton');
        const container = document.getElementById('decompositionResultContainer');
        
        if (indicator) indicator.style.display = 'none';
        if (button) button.style.display = 'none';
        if (container) container.style.display = 'none';
    }
}

// 全局函数，供HTML调用
window.showComplexitySettings = function() {
    // 显示复杂度设置对话框
    const settingsHTML = `
        <div id="complexitySettingsModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="glass-morphism rounded-xl p-6 w-full max-w-md text-blue-100">
                <h3 class="text-lg font-semibold mb-4">复杂度分析设置</h3>
                
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium mb-2">拆解阈值</label>
                        <input type="range" id="thresholdSlider" min="0.1" max="1" step="0.1" 
                               value="${window.taskDecompositionUI?.complexityThreshold || 0.7}"
                               class="w-full">
                        <div class="flex justify-between text-xs text-gray-400 mt-1">
                            <span>10%</span>
                            <span>100%</span>
                        </div>
                    </div>
                    
                    <div class="text-xs text-gray-400">
                        <p>当任务复杂度超过设定阈值时，将显示任务拆解按钮。</p>
                    </div>
                </div>
                
                <div class="flex justify-end space-x-3 mt-6">
                    <button onclick="closeComplexitySettings()" class="px-4 py-2 rounded-lg hover:bg-white hover:bg-opacity-10 transition-all">
                        取消
                    </button>
                    <button onclick="saveComplexitySettings()" class="px-4 py-2 bg-purple-600 rounded-lg hover:bg-purple-700 transition-all text-white">
                        保存
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', settingsHTML);
};

window.closeComplexitySettings = function() {
    const modal = document.getElementById('complexitySettingsModal');
    if (modal) {
        modal.remove();
    }
};

window.saveComplexitySettings = function() {
    const slider = document.getElementById('thresholdSlider');
    if (slider && window.taskDecompositionUI) {
        window.taskDecompositionUI.updateThreshold(parseFloat(slider.value));
    }
    window.closeComplexitySettings();
};

window.requestTaskDecomposition = function() {
    if (window.metaAgentChatManager && window.taskDecompositionUI) {
        window.taskDecompositionUI.startDecomposition();
        window.metaAgentChatManager.requestDecomposition();
    }
};

window.toggleEditMode = function() {
    if (window.taskDecompositionUI) {
        window.taskDecompositionUI.toggleEditMode();
    }
};

window.regenerateDecomposition = function() {
    if (window.metaAgentChatManager && window.taskDecompositionUI) {
        window.taskDecompositionUI.startDecomposition();
        window.metaAgentChatManager.requestDecomposition();
    }
};

window.cancelDecomposition = function() {
    if (window.taskDecompositionUI) {
        window.taskDecompositionUI.hideDecompositionResult();
    }
};

window.confirmDecomposition = function() {
    if (window.metaAgentChatManager && window.taskDecompositionUI) {
        const result = window.taskDecompositionUI.decompositionResult;
        if (result) {
            // 调用任务创建逻辑
            window.metaAgentChatManager.finalizeTask({
                decomposed: true,
                mainTask: result.mainTask,
                subtasks: result.subtasks,
                dependencies: result.dependencies
            });
        }
    }
};

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TaskDecompositionUI;
} else {
    window.TaskDecompositionUI = TaskDecompositionUI;
}