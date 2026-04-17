import { create } from 'zustand'

interface AppState {
  collapsed: boolean
  setCollapsed: (collapsed: boolean) => void

  currentSessionId: string | null
  setCurrentSessionId: (id: string | null) => void

  searchResults: any[]
  setSearchResults: (results: any[]) => void

  chatMessages: ChatMessage[]
  addChatMessage: (message: ChatMessage) => void
  clearChatMessages: () => void
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export const useAppStore = create<AppState>((set) => ({
  collapsed: false,
  setCollapsed: (collapsed) => set({ collapsed }),

  currentSessionId: null,
  setCurrentSessionId: (id) => set({ currentSessionId: id }),

  searchResults: [],
  setSearchResults: (results) => set({ searchResults: results }),

  chatMessages: [],
  addChatMessage: (message) =>
    set((state) => ({
      chatMessages: [...state.chatMessages, message]
    })),
  clearChatMessages: () => set({ chatMessages: [] })
}))
