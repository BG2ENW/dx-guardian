// DX Guardian Web Push 前端模块
let swRegistration = null;
let pushSubscribed = false;

// 初始化 Service Worker 和推送订阅
async function initWebPush() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        console.log('[Push] 浏览器不支持 Web Push');
        updatePushButton(false, '不支持');
        return;
    }

    try {
        swRegistration = await navigator.serviceWorker.register('/sw.js');
        console.log('[Push] Service Worker 注册成功');

        // 等待 SW 就绪
        await navigator.serviceWorker.ready;

        // 检查是否已有订阅
        const subscription = await swRegistration.pushManager.getSubscription();
        pushSubscribed = !!subscription;
        updatePushButton(pushSubscribed);
    } catch (e) {
        console.error('[Push] 注册失败:', e);
        updatePushButton(false, '注册失败');
    }
}

// 订阅推送
async function subscribePush() {
    if (!swRegistration) return;

    try {
        // 获取 VAPID 公钥
        const resp = await fetch('/api/push/public_key');
        if (!resp.ok) throw new Error('无法获取 VAPID 公钥');
        const { public_key } = await resp.json();

        // 转换公钥为 Uint8Array
        const applicationServerKey = urlBase64ToUint8Array(public_key);

        // 请求通知权限
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
            alert('请允许通知权限以启用推送');
            return;
        }

        // 订阅
        const subscription = await swRegistration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey
        });

        // 发送到服务器
        const subJson = subscription.toJSON();
        await fetch('/api/push/subscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(subJson)
        });

        pushSubscribed = true;
        updatePushButton(true);
        console.log('[Push] 订阅成功');
    } catch (e) {
        console.error('[Push] 订阅失败:', e);
        updatePushButton(false, '订阅失败');
    }
}

// 取消订阅
async function unsubscribePush() {
    if (!swRegistration) return;

    try {
        const subscription = await swRegistration.pushManager.getSubscription();
        if (subscription) {
            // 通知服务器
            await fetch('/api/push/unsubscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ endpoint: subscription.endpoint })
            });
            // 取消浏览器订阅
            await subscription.unsubscribe();
        }
        pushSubscribed = false;
        updatePushButton(false);
        console.log('[Push] 已取消订阅');
    } catch (e) {
        console.error('[Push] 取消订阅失败:', e);
    }
}

// 切换订阅状态
function togglePush() {
    if (pushSubscribed) {
        unsubscribePush();
    } else {
        subscribePush();
    }
}

// 更新按钮状态
function updatePushButton(subscribed, extra = '') {
    const btn = document.getElementById('push-toggle-btn');
    const status = document.getElementById('push-status');
    if (btn) {
        btn.textContent = subscribed ? '🔕 关闭推送' : '🔔 开启推送';
        btn.style.background = subscribed ? 'rgba(76,175,80,0.3)' : 'rgba(233,69,96,0.3)';
        btn.style.borderColor = subscribed ? '#4CAF50' : '#e94560';
        btn.style.color = subscribed ? '#4CAF50' : '#e94560';
    }
    if (status) {
        status.textContent = subscribed ? '已开启' : (extra || '未开启');
        status.style.color = subscribed ? '#4CAF50' : '#666';
    }
}

// 测试推送
async function testPush() {
    try {
        const resp = await fetch('/api/push/test', { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            alert('测试推送已发送！请检查浏览器通知。');
        } else {
            alert('推送失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('推送测试失败: ' + e.message);
    }
}

// 工具函数：base64url → Uint8Array
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; i++) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    initWebPush();
});
