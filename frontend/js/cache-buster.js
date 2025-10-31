/**
 * 缓存清理工具
 * 为所有脚本和样式表添加版本参数，防止浏览器缓存
 */

(function() {
    'use strict';
    
    // 生成版本号（基于当前时间戳）
    const version = Date.now();
    
    // 为所有脚本标签添加版本参数
    function addVersionToScripts() {
        const scripts = document.querySelectorAll('script[src]');
        scripts.forEach(script => {
            const src = script.src;
            if (src && !src.includes('?v=') && !src.includes('cdn.')) {
                // 只对本地脚本添加版本参数，跳过CDN资源
                const separator = src.includes('?') ? '&' : '?';
                script.src = src + separator + 'v=' + version;
            }
        });
    }
    
    // 为所有样式表添加版本参数
    function addVersionToStyles() {
        const links = document.querySelectorAll('link[rel="stylesheet"][href]');
        links.forEach(link => {
            const href = link.href;
            if (href && !href.includes('?v=') && !href.includes('cdn.')) {
                // 只对本地样式表添加版本参数，跳过CDN资源
                const separator = href.includes('?') ? '&' : '?';
                link.href = href + separator + 'v=' + version;
            }
        });
    }
    
    // 动态加载脚本时添加版本参数
    function loadScriptWithVersion(src, callback) {
        const script = document.createElement('script');
        const separator = src.includes('?') ? '&' : '?';
        script.src = src + separator + 'v=' + version;
        script.onload = callback;
        script.onerror = function() {
            console.error('Failed to load script:', src);
        };
        document.head.appendChild(script);
        return script;
    }
    
    // 动态加载样式表时添加版本参数
    function loadStyleWithVersion(href) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        const separator = href.includes('?') ? '&' : '?';
        link.href = href + separator + 'v=' + version;
        document.head.appendChild(link);
        return link;
    }
    
    // 清除本地存储中的缓存数据
    function clearLocalCache() {
        try {
            // 清除可能的缓存键
            const cacheKeys = [
                'meta_agent_conversation_state',
                'xuexing_tasks',
                'xuexing_chat_history',
                'xuexing_user_settings'
            ];
            
            cacheKeys.forEach(key => {
                const data = localStorage.getItem(key);
                if (data) {
                    try {
                        const parsed = JSON.parse(data);
                        // 检查数据是否过期（超过1小时）
                        if (parsed.timestamp) {
                            const age = Date.now() - new Date(parsed.timestamp).getTime();
                            if (age > 3600000) { // 1小时
                                localStorage.removeItem(key);
                                console.log('Cleared expired cache:', key);
                            }
                        }
                    } catch (e) {
                        // 如果解析失败，直接删除
                        localStorage.removeItem(key);
                    }
                }
            });
        } catch (error) {
            console.warn('Failed to clear local cache:', error);
        }
    }
    
    // 强制刷新页面（绕过缓存）
    function forceRefresh() {
        // 添加时间戳参数到当前URL
        const url = new URL(window.location);
        url.searchParams.set('_t', Date.now());
        window.location.href = url.toString();
    }
    
    // 检查是否需要强制刷新
    function checkForceRefresh() {
        const urlParams = new URLSearchParams(window.location.search);
        const forceParam = urlParams.get('force');
        
        if (forceParam === 'true') {
            // 清除强制刷新参数
            urlParams.delete('force');
            const newUrl = window.location.pathname + 
                          (urlParams.toString() ? '?' + urlParams.toString() : '');
            window.history.replaceState({}, '', newUrl);
            
            // 清除所有缓存
            clearLocalCache();
            
            // 显示刷新提示
            console.log('🔄 强制刷新完成，缓存已清除');
        }
    }
    
    // 添加调试信息
    function addDebugInfo() {
        if (window.location.search.includes('debug=true')) {
            console.log('🐛 缓存清理工具调试信息:');
            console.log('版本号:', version);
            console.log('当前URL:', window.location.href);
            console.log('用户代理:', navigator.userAgent);
            console.log('本地存储项数:', localStorage.length);
        }
    }
    
    // 导出工具函数到全局
    window.CacheBuster = {
        version: version,
        loadScript: loadScriptWithVersion,
        loadStyle: loadStyleWithVersion,
        clearCache: clearLocalCache,
        forceRefresh: forceRefresh,
        addVersionToScripts: addVersionToScripts,
        addVersionToStyles: addVersionToStyles
    };
    
    // 页面加载时执行
    document.addEventListener('DOMContentLoaded', function() {
        checkForceRefresh();
        addDebugInfo();
        
        // 延迟执行，确保所有脚本都已加载
        setTimeout(() => {
            addVersionToScripts();
            addVersionToStyles();
        }, 100);
    });
    
    // 在页面卸载前清理过期缓存
    window.addEventListener('beforeunload', function() {
        clearLocalCache();
    });
    
    console.log('🚀 缓存清理工具已加载，版本:', version);
})();