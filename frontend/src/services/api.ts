import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export interface SearchResult {
  id: number
  title: string
  content: string
  source: string
  source_url: string
  publish_time: string
  sentiment?: string
  score: number
}

export interface SearchResponse {
  query: string
  results: SearchResult[]
  total: number
  elapsed_time: number
}

export interface BriefingData {
  id: number
  topic: string
  generated_at: string
  time_range: number
  summary: string
  sections: any[]
  hot_keywords: string[]
  sentiment_distribution: Record<string, number>
  source_distribution: Record<string, number>
}

export interface HotTopic {
  keyword: string
  frequency: number
  trend: number
  is_hot: boolean
}

export const searchAPI = {
  search: async (query: string, topK: number = 10): Promise<SearchResponse> => {
    const response = await api.post('/search', { query, top_k: topK })
    return response.data
  }
}

export const chatAPI = {
  sendMessage: async (message: string, sessionId?: string) => {
    const params = new URLSearchParams({ message })
    if (sessionId) params.append('session_id', sessionId)
    const response = await api.post(`/chat?${params.toString()}`)
    return response.data
  }
}

export const briefingAPI = {
  generate: async (topic: string, timeRange: number = 24): Promise<BriefingData> => {
    const response = await api.post('/briefing', {
      topic,
      time_range: timeRange,
      include_sentiment: true,
      include_trend: true
    })
    return response.data
  },

  list: async (limit: number = 20): Promise<BriefingData[]> => {
    const response = await api.get(`/briefings?limit=${limit}`)
    return response.data
  }
}

export const statisticsAPI = {
  getSentiment: async (timeRange: number = 24) => {
    const response = await api.get(`/statistics/sentiment?time_range=${timeRange}`)
    return response.data
  },

  getKeywords: async (timeRange: number = 24) => {
    const response = await api.get(`/statistics/keywords?time_range=${timeRange}`)
    return response.data
  },

  getSources: async (timeRange: number = 24) => {
    const response = await api.get(`/statistics/sources?time_range=${timeRange}`)
    return response.data
  },

  getTrend: async (timeRange: number = 24) => {
    const response = await api.get(`/statistics/trend?time_range=${timeRange}`)
    return response.data
  }
}

export const hotTopicsAPI = {
  list: async (limit: number = 10, timeRange: number = 24): Promise<HotTopic[]> => {
    const response = await api.get(`/hot-topics?limit=${limit}&time_range=${timeRange}`)
    return response.data.data
  }
}

export const yuqingAPI = {
  list: async (limit: number = 20, offset: number = 0, source?: string) => {
    let url = `/yuqing?limit=${limit}&offset=${offset}`
    if (source) url += `&source=${source}`
    const response = await api.get(url)
    return response.data
  }
}

export const crawlerAPI = {
  crawlUrl: async (url: string, source: string = 'news') => {
    const response = await api.post(`/crawl/url?url=${encodeURIComponent(url)}&source=${source}`)
    return response.data
  },

  crawlRss: async (feedUrl: string, source: string = 'news') => {
    const response = await api.post(`/crawl/rss?feed_url=${encodeURIComponent(feedUrl)}&source=${source}`)
    return response.data
  }
}

export default api
