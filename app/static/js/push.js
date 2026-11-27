/* Suscripción del dispositivo a notificaciones push del chat (PC y teléfono). */
(function () {
    const supported = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
    const state = { supported, active: false, enabled: false };
    window.intranetPush = state;

    function urlBase64ToUint8Array(base64) {
        const padding = '='.repeat((4 - (base64.length % 4)) % 4);
        const raw = atob((base64 + padding).replace(/-/g, '+').replace(/_/g, '/'));
        return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
    }

    function csrf() {
        const match = document.cookie.match(/(?:^|; )csrf_token=([^;]*)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    async function post(url, body) {
        return fetch(url, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json', 'x-csrf-token': csrf() },
            body: JSON.stringify(body),
        });
    }

    async function subscribe() {
        const keyResponse = await fetch('/api/admin-chat/push/key', { credentials: 'include' });
        if (!keyResponse.ok) return false;
        const { enabled, public_key: publicKey } = await keyResponse.json();
        state.enabled = Boolean(enabled);
        if (!enabled || !publicKey) return false;

        const registration = await navigator.serviceWorker.register('/sw.js', { scope: '/' });
        await navigator.serviceWorker.ready;
        let subscription = await registration.pushManager.getSubscription();
        if (!subscription) {
            subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(publicKey),
            });
        }
        const response = await post('/api/admin-chat/push/subscribe', subscription.toJSON());
        state.active = response.ok;
        document.dispatchEvent(new CustomEvent('intranet-push-change', { detail: state }));
        return state.active;
    }

    /** Pide permiso (requiere un clic del usuario) y suscribe este dispositivo. */
    state.enable = async function () {
        if (!supported) return { ok: false, reason: 'unsupported' };
        const permission = Notification.permission === 'default'
            ? await Notification.requestPermission()
            : Notification.permission;
        if (permission !== 'granted') return { ok: false, reason: 'denied' };
        try {
            const ok = await subscribe();
            return { ok, reason: ok ? null : (state.enabled ? 'error' : 'disabled') };
        } catch (error) {
            console.debug('No fue posible activar push:', error);
            return { ok: false, reason: 'error' };
        }
    };

    // Si el permiso ya estaba concedido, se renueva la suscripción en silencio.
    if (supported && Notification.permission === 'granted') {
        subscribe().catch(error => console.debug('Suscripción push no disponible:', error));
    }
})();
