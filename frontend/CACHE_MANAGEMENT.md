# 缓存管理指南

## 问题描述
浏览器缓存可能导致页面修改后不生效，特别是JavaScript和CSS文件的更新。

## 解决方案

### 1. 自动缓存控制
前端服务器已配置自动缓存控制：
- 所有响应都包含 `Cache-Control: no-cache, no-store, must-revalidate`
- 自动为本地资源添加时间戳版本参数

### 2. 缓存清理工具
已集成 `js/cache-buster.js` 工具：
- 自动为脚本和样式表添加版本参数
- 清理过期的本地存储数据
- 提供强制刷新功能

### 3. 手动清除缓存方法

#### 方法一：使用测试页面
访问 `http://localhost:3000/test-meta-agent-chat.html`
点击 "🔄 强制清除缓存并刷新" 按钮

#### 方法二：URL参数
在任何页面URL后添加 `?force=true` 参数：
```
http://localhost:3000/88.html?force=true
```

#### 方法三：浏览器开发者工具
1. 按 F12 打开开发者工具
2. 右键点击刷新按钮
3. 选择 "清空缓存并硬性重新加载"

#### 方法四：JavaScript控制台
在浏览器控制台执行：
```javascript
// 清除所有缓存并刷新
window.CacheBuster.forceRefresh();

// 仅清除本地存储
window.CacheBuster.clearCache();
```

### 4. 调试模式
在URL中添加 `debug=true` 参数查看缓存调试信息：
```
http://localhost:3000/88.html?debug=true
```

### 5. 版本控制
每次页面加载都会生成新的版本号（基于时间戳），确保资源不被缓存。

## 最佳实践

1. **开发时**：使用测试页面的强制刷新功能
2. **调试时**：启用调试模式查看缓存状态
3. **部署时**：确保服务器配置了正确的缓存控制头

## 常见问题

### Q: 为什么修改后的JavaScript函数不生效？
A: 浏览器可能缓存了旧版本的JS文件，使用强制刷新功能。

### Q: 如何确认缓存已清除？
A: 在控制台查看是否有 "🔄 强制刷新完成，缓存已清除" 消息。

### Q: 本地存储数据丢失了？
A: 强制清除缓存会清空所有本地存储，这是正常行为。

## 技术细节

### 缓存控制头
```
Cache-Control: no-cache, no-store, must-revalidate
Pragma: no-cache
Expires: 0
```

### 版本参数格式
```
script.js?v=1698364800000
style.css?v=1698364800000
```

### 清理的本地存储键
- `meta_agent_conversation_state`
- `xuexing_tasks`
- `xuexing_chat_history`
- `xuexing_user_settings`