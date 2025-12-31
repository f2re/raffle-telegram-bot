<template>
  <div id="app" :class="{ 'telegram-theme': isTelegram }">
    <header class="app-header">
      <h1>🎲 Розыгрыш TON</h1>

      <div v-if="!isConnected" class="connect-section">
        <button @click="connectWallet" class="connect-btn">
          💎 Подключить TON кошелек
        </button>
      </div>

      <div v-else class="wallet-info">
        <span class="wallet-address">
          💎 {{ shortAddress }}
        </span>
        <button @click="disconnectWallet" class="disconnect-btn">
          ✕
        </button>
      </div>
    </header>

    <main class="app-main">
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
        <p>Загрузка...</p>
      </div>

      <div v-else-if="raffle" class="raffle-container">
        <div class="raffle-card">
          <h2>Текущий розыгрыш</h2>

          <div class="raffle-stats">
            <div class="stat-item">
              <span class="stat-label">💰 Взнос:</span>
              <span class="stat-value">{{ raffle.entry_fee }} TON</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">🎯 Приз:</span>
              <span class="stat-value">{{ prizePool }} TON</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">👥 Участников:</span>
              <span class="stat-value">
                {{ raffle.participants_count }}/{{ raffle.min_participants }}
              </span>
            </div>
            <div class="stat-item">
              <span class="stat-label">📊 Статус:</span>
              <span class="stat-value status" :class="raffle.status">
                {{ statusText }}
              </span>
            </div>
          </div>

          <div class="progress-section">
            <div class="progress-bar">
              <div
                class="progress-fill"
                :style="{ width: progressPercent + '%' }"
              ></div>
            </div>
            <p class="progress-text">
              {{ progressText }}
            </p>
          </div>

          <button
            v-if="raffle.status === 'collecting' && isConnected"
            @click="joinRaffle"
            :disabled="isJoining || raffle.user_participated"
            class="join-btn"
            :class="{ 'already-joined': raffle.user_participated }"
          >
            <span v-if="isJoining">⏳ Обработка...</span>
            <span v-else-if="raffle.user_participated">✅ Вы участвуете</span>
            <span v-else>🎲 Участвовать за {{ raffle.entry_fee }} TON</span>
          </button>

          <button
            v-else-if="!isConnected"
            @click="connectWallet"
            class="join-btn connect-required"
          >
            💎 Подключите кошелек для участия
          </button>

          <div v-else-if="raffle.status === 'running'" class="status-message">
            🔄 Определяем победителя...
          </div>

          <div v-else-if="raffle.status === 'completed'" class="status-message">
            ✅ Розыгрыш завершен
          </div>
        </div>

        <div class="participants-list" v-if="participants.length">
          <h3>👥 Участники ({{ participants.length }})</h3>
          <ul>
            <li v-for="p in participants" :key="p.id" class="participant-item">
              <span class="participant-name">
                {{ p.username ? '@' + p.username : p.first_name }}
              </span>
              <span class="participant-time">{{ formatTime(p.joined_at) }}</span>
            </li>
          </ul>
        </div>
      </div>

      <div v-else class="no-raffle">
        <div class="no-raffle-icon">😔</div>
        <p>Нет активного розыгрыша</p>
        <p class="sub-text">Скоро появится новый!</p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useTonConnect } from './composables/useTonConnect'
import { useTelegram } from './composables/useTelegram'
import { raffleApi } from './api/raffle'
import type { Raffle, Participant } from './api/types'

const { telegram, initData, userId, isTelegram } = useTelegram()
const { wallet, isConnected, connect, disconnect, sendTransaction } = useTonConnect()

const raffle = ref<Raffle | null>(null)
const participants = ref<Participant[]>([])
const loading = ref(true)
const isJoining = ref(false)

const shortAddress = computed(() => {
  if (!wallet.value) return ''
  const addr = wallet.value.account.address
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`
})

const prizePool = computed(() => {
  if (!raffle.value) return '0'
  const total = raffle.value.entry_fee * raffle.value.participants_count
  const commission = total * 0.12
  return (total - commission).toFixed(2)
})

const progressPercent = computed(() => {
  if (!raffle.value) return 0
  return Math.min(
    (raffle.value.participants_count / raffle.value.min_participants) * 100,
    100
  )
})

const progressText = computed(() => {
  if (!raffle.value) return ''
  const remaining = raffle.value.min_participants - raffle.value.participants_count
  return remaining > 0
    ? `Осталось участников: ${remaining}`
    : '✨ Минимум набран! Розыгрыш скоро начнется'
})

const statusText = computed(() => {
  const statuses: Record<string, string> = {
    'collecting': '🟢 Идет набор',
    'ready': '🟡 Готов к старту',
    'running': '🔄 Определяем победителя',
    'completed': '✅ Завершен'
  }
  return statuses[raffle.value?.status || ''] || raffle.value?.status
})

async function fetchRaffle() {
  try {
    const data = await raffleApi.getCurrent(initData.value)
    raffle.value = data
  } catch (error: any) {
    console.error('Failed to fetch raffle:', error)
    if (error.message !== 'HTTP 404') {
      telegram.value?.showAlert('Ошибка загрузки данных')
    }
  } finally {
    loading.value = false
  }
}

async function fetchParticipants() {
  if (!raffle.value) return
  try {
    const data = await raffleApi.getParticipants(raffle.value.id, initData.value)
    participants.value = data
  } catch (error) {
    console.error('Failed to fetch participants:', error)
  }
}

async function connectWallet() {
  try {
    await connect()
    telegram.value?.showAlert('✅ Кошелек подключен!')
  } catch (error) {
    console.error('Failed to connect wallet:', error)
    telegram.value?.showAlert('Ошибка подключения кошелька')
  }
}

async function disconnectWallet() {
  await disconnect()
  telegram.value?.showAlert('Кошелек отключен')
}

async function joinRaffle() {
  if (!raffle.value || !wallet.value) return

  isJoining.value = true
  telegram.value?.HapticFeedback?.impactOccurred('medium')

  try {
    const comment = `raffle_${raffle.value.id}_user_${userId.value}`

    const result = await sendTransaction({
      address: import.meta.env.VITE_TON_WALLET_ADDRESS,
      amount: raffle.value.entry_fee,
      comment
    })

    if (!result) {
      throw new Error('Transaction cancelled')
    }

    await raffleApi.join({
      raffle_id: raffle.value.id,
      transaction_hash: result.boc,
      wallet_address: wallet.value.account.address
    }, initData.value)

    telegram.value?.HapticFeedback?.notificationOccurred('success')
    telegram.value?.showAlert('✅ Оплата успешна! Вы участвуете в розыгрыше.')

    await fetchRaffle()
    await fetchParticipants()

  } catch (error: any) {
    console.error('Join raffle failed:', error)
    telegram.value?.HapticFeedback?.notificationOccurred('error')
    telegram.value?.showAlert(`❌ Ошибка: ${error.message || 'Попробуйте снова'}`)
  } finally {
    isJoining.value = false
  }
}

function formatTime(timestamp: string) {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(async () => {
  if (telegram.value) {
    telegram.value.ready()
    telegram.value.expand()
    telegram.value.enableClosingConfirmation()

    if (telegram.value.BackButton) {
      telegram.value.BackButton.show()
      telegram.value.BackButton.onClick(() => {
        telegram.value?.close()
      })
    }
  }

  await fetchRaffle()
  if (raffle.value) {
    await fetchParticipants()

    setInterval(() => {
      fetchRaffle()
      fetchParticipants()
    }, 10000)
  }
})
</script>

<style scoped>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  color: #ffffff;
}

.telegram-theme {
  background: var(--tg-theme-bg-color, linear-gradient(135deg, #667eea 0%, #764ba2 100%));
  color: var(--tg-theme-text-color, #ffffff);
}

.app-header {
  padding: 20px;
  text-align: center;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.app-header h1 {
  font-size: 24px;
  margin-bottom: 15px;
  font-weight: 700;
}

.connect-section {
  margin-top: 10px;
}

.connect-btn {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
}

.connect-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
}

.wallet-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 10px;
}

.wallet-address {
  background: rgba(255, 255, 255, 0.2);
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
}

.disconnect-btn {
  background: rgba(239, 68, 68, 0.8);
  color: white;
  border: none;
  padding: 8px 12px;
  border-radius: 50%;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.disconnect-btn:hover {
  background: rgba(239, 68, 68, 1);
}

.app-main {
  padding: 20px;
  max-width: 600px;
  margin: 0 auto;
}

.loading {
  text-align: center;
  padding: 60px 20px;
}

.spinner {
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-top: 4px solid white;
  border-radius: 50%;
  width: 50px;
  height: 50px;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.raffle-container {
  animation: fadeIn 0.5s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.raffle-card {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 24px;
  margin-bottom: 20px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.raffle-card h2 {
  font-size: 20px;
  margin-bottom: 20px;
  text-align: center;
  font-weight: 700;
}

.raffle-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 20px;
}

.stat-item {
  background: rgba(255, 255, 255, 0.1);
  padding: 12px;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 13px;
  opacity: 0.9;
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
}

.stat-value.status {
  font-size: 14px;
  padding: 4px 8px;
  border-radius: 8px;
  display: inline-block;
}

.stat-value.status.collecting {
  background: rgba(34, 197, 94, 0.3);
}

.stat-value.status.ready {
  background: rgba(234, 179, 8, 0.3);
}

.stat-value.status.running {
  background: rgba(59, 130, 246, 0.3);
}

.stat-value.status.completed {
  background: rgba(168, 85, 247, 0.3);
}

.progress-section {
  margin-bottom: 20px;
}

.progress-bar {
  background: rgba(255, 255, 255, 0.2);
  height: 12px;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  background: linear-gradient(90deg, #10b981 0%, #059669 100%);
  height: 100%;
  transition: width 0.5s ease;
  border-radius: 6px;
}

.progress-text {
  text-align: center;
  font-size: 14px;
  opacity: 0.9;
}

.join-btn {
  width: 100%;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  border: none;
  padding: 16px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
}

.join-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(16, 185, 129, 0.5);
}

.join-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.join-btn.already-joined {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
}

.join-btn.connect-required {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.status-message {
  text-align: center;
  padding: 16px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
}

.participants-list {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.participants-list h3 {
  font-size: 18px;
  margin-bottom: 16px;
  font-weight: 700;
}

.participants-list ul {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.participant-item {
  background: rgba(255, 255, 255, 0.1);
  padding: 12px;
  border-radius: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.participant-name {
  font-weight: 600;
  font-size: 14px;
}

.participant-time {
  font-size: 12px;
  opacity: 0.7;
}

.no-raffle {
  text-align: center;
  padding: 60px 20px;
}

.no-raffle-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.no-raffle p {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
}

.no-raffle .sub-text {
  font-size: 14px;
  opacity: 0.7;
}
</style>
