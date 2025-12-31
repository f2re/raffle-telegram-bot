import { ref, onMounted } from 'vue'
import { TonConnectUI, Wallet } from '@tonconnect/ui'
import { toNano, beginCell } from '@ton/core'

interface SendTransactionParams {
  address: string
  amount: number
  comment?: string
}

export function useTonConnect() {
  const tonConnectUI = ref<TonConnectUI | null>(null)
  const wallet = ref<Wallet | null>(null)
  const isConnected = ref(false)

  onMounted(async () => {
    const manifestUrl = import.meta.env.VITE_TON_CONNECT_MANIFEST_URL

    tonConnectUI.value = new TonConnectUI({
      manifestUrl: manifestUrl || '/tonconnect-manifest.json',
      buttonRootId: null
    })

    tonConnectUI.value.onStatusChange((w: Wallet | null) => {
      wallet.value = w
      isConnected.value = !!w
    })

    // Restore connection
    const currentWallet = tonConnectUI.value.wallet
    if (currentWallet) {
      wallet.value = currentWallet
      isConnected.value = true
    }
  })

  async function connect() {
    if (!tonConnectUI.value) throw new Error('TonConnect not initialized')
    await tonConnectUI.value.openModal()
  }

  async function disconnect() {
    if (!tonConnectUI.value) return
    await tonConnectUI.value.disconnect()
    wallet.value = null
    isConnected.value = false
  }

  async function sendTransaction(params: SendTransactionParams) {
    if (!tonConnectUI.value || !isConnected.value) {
      throw new Error('Wallet not connected')
    }

    let payload: string | undefined = undefined

    if (params.comment) {
      const body = beginCell()
        .storeUint(0, 32)
        .storeStringTail(params.comment)
        .endCell()
      payload = body.toBoc().toString('base64')
    }

    const transaction = {
      validUntil: Math.floor(Date.now() / 1000) + 600,
      messages: [
        {
          address: params.address,
          amount: toNano(params.amount).toString(),
          payload
        }
      ]
    }

    return await tonConnectUI.value.sendTransaction(transaction)
  }

  return {
    tonConnectUI,
    wallet,
    isConnected,
    connect,
    disconnect,
    sendTransaction
  }
}
