import { apiFetch } from './client'

export async function fetchVapidPublicKey() {
  const data = await apiFetch('/api/notifications/vapid-public-key/')
  return data.public_key
}

export function registerPushSubscription(subscription) {
  return apiFetch('/api/notifications/push-subscriptions/', {
    method: 'POST',
    body: subscription.toJSON(),
  })
}
