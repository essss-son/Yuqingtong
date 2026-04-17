import { useState } from 'react'
import { Input, Card, List, Tag, Empty, Spin, Space, Slider, message } from 'antd'
import { SearchOutlined, ClockCircleOutlined, LinkOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { searchAPI, SearchResult } from '../services/api'

const { Search: SearchInput } = Input

export default function Search() {
  const [loading, setLoading] = useState(false)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [topK, setTopK] = useState(10)

  const handleSearch = async (value: string) => {
    if (!value.trim()) {
      message.warning('请输入搜索关键词')
      return
    }

    setLoading(true)
    setQuery(value)

    try {
      const response = await searchAPI.search(value, topK)
      const searchResults = response.results.map((r: any) => {
        const item = r.item || r
        return {
          id: item.id,
          title: item.title || '未知标题',
          content: item.content || '',
          source: item.source || 'unknown',
          source_url: item.source_url || '',
          publish_time: item.publish_time || '',
          sentiment: item.sentiment,
          score: r.score || 0
        }
      })
      setResults(searchResults)
    } catch (error) {
      message.error('搜索失败，请稍后重试')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const getSentimentTag = (sentiment?: string) => {
    if (!sentiment) return null
    const config: Record<string, { color: string; text: string }> = {
      positive: { color: 'success', text: '正面' },
      negative: { color: 'error', text: '负面' },
      neutral: { color: 'warning', text: '中性' }
    }
    const { color, text } = config[sentiment] || { color: 'default', text: sentiment }
    return <Tag color={color}>{text}</Tag>
  }

  const getSourceTag = (source: string) => {
    const colorMap: Record<string, string> = {
      news: 'blue',
      weibo: 'red',
      wechat: 'green',
      social: 'purple',
      forum: 'orange'
    }
    return <Tag color={colorMap[source] || 'default'}>{source}</Tag>
  }

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <SearchInput
            placeholder="输入关键词搜索舆情内容..."
            allowClear
            enterButton={<><SearchOutlined /> 搜索</>}
            size="large"
            loading={loading}
            onSearch={handleSearch}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span>返回结果数：</span>
            <Slider
              min={5}
              max={50}
              value={topK}
              onChange={setTopK}
              style={{ width: 200 }}
              marks={{ 5: '5', 20: '20', 50: '50' }}
            />
            <span>{topK} 条</span>
          </div>
        </Space>
      </Card>

      {loading ? (
        <div className="loading-container">
          <Spin size="large" tip="搜索中..." />
        </div>
      ) : results.length > 0 ? (
        <List
          itemLayout="vertical"
          dataSource={results}
          renderItem={(item, index) => (
            <List.Item
              key={item.id}
              extra={
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>
                    {(item.score * 100).toFixed(0)}%
                  </div>
                  <div style={{ fontSize: 12, color: '#999' }}>相关度</div>
                </div>
              }
            >
              <List.Item.Meta
                title={
                  <Space>
                    <span style={{ color: '#666', fontSize: 14 }}>#{index + 1}</span>
                    <a href={item.source_url} target="_blank" rel="noopener noreferrer">
                      {item.title}
                    </a>
                  </Space>
                }
                description={
                  <Space>
                    {getSourceTag(item.source)}
                    {getSentimentTag(item.sentiment)}
                    {item.publish_time && (
                      <Tag icon={<ClockCircleOutlined />}>
                        {dayjs(item.publish_time).format('YYYY-MM-DD HH:mm')}
                      </Tag>
                    )}
                  </Space>
                }
              />
              <div style={{ color: '#666', lineHeight: 1.8 }}>
                {item.content.slice(0, 300)}...
              </div>
              <div style={{ marginTop: 8 }}>
                <a href={item.source_url} target="_blank" rel="noopener noreferrer">
                  <LinkOutlined /> 查看原文
                </a>
              </div>
            </List.Item>
          )}
        />
      ) : (
        <Empty
          description={query ? '未找到相关结果' : '输入关键词开始搜索'}
          style={{ marginTop: 100 }}
        />
      )}
    </div>
  )
}
