export interface Raffle {
  id: number
  entry_fee: number
  participants_count: number
  min_participants: number
  status: 'collecting' | 'ready' | 'running' | 'completed'
  user_participated: boolean
  created_at?: string
  started_at?: string
}

export interface Participant {
  id: number
  username: string | null
  first_name: string
  joined_at: string
}

export interface JoinRaffleRequest {
  raffle_id: number
  transaction_hash: string
  wallet_address: string
}

export interface JoinRaffleResponse {
  status: string
  participant_id: number
}

export interface ApiError {
  detail: string
}
