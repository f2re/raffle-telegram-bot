import { ref, onMounted } from 'vue'

declare global {
  interface Window {
    Telegram?: {
      WebApp: any
    }
  }
}

export function useTelegram() {
  const telegram = ref<any>(null)
  const initData = ref('')
  const userId = ref<number | null>(null)
  const isTelegram = ref(false)
  const user = ref<any>(null)

  onMounted(() => {
    if (typeof window !== 'undefined' && window.Telegram?.WebApp) {
      telegram.value = window.Telegram.WebApp
      initData.value = telegram.value.initData
      userId.value = telegram.value.initDataUnsafe.user?.id || null
      user.value = telegram.value.initDataUnsafe.user || null
      isTelegram.value = true
    }
  })

  return {
    telegram,
    initData,
    userId,
    user,
    isTelegram
  }
}
