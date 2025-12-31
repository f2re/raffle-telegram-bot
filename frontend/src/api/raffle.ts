import type { Raffle, Participant, JoinRaffleRequest, JoinRaffleResponse } from './types'

const API_URL = import.meta.env.VITE_API_URL || '/api'

class RaffleAPI {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    initData?: string
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    if (initData) {
      headers['Authorization'] = `tma ${initData}`
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    return response.json()
  }

  async getCurrent(initData: string): Promise<Raffle> {
    return this.request<Raffle>('/raffle/current', {}, initData)
  }

  async getParticipants(raffleId: number, initData: string): Promise<Participant[]> {
    return this.request<Participant[]>(`/raffle/${raffleId}/participants`, {}, initData)
  }

  async join(data: JoinRaffleRequest, initData: string): Promise<JoinRaffleResponse> {
    return this.request<JoinRaffleResponse>(
      '/raffle/join',
      {
        method: 'POST',
        body: JSON.stringify(data),
      },
      initData
    )
  }
}

export const raffleApi = new RaffleAPI()
