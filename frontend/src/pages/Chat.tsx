import { useState, useRef, useEffect } from 'react'
import { Input, Button, Card, Avatar, Spin, message, Space, Tag } from 'antd'
import { SendOutlined, RobotOutlined, UserOutlined, ClearOutlined } from '@ant-design/icons'
import { chatAPI } from '../services/api'
import ReactMarkdown from 'react-markdown'

const { TextArea } = Input

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleSend = async () => {
    if (!input.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await chatAPI.sendMessage(input, sessionId || undefined)

      if (response.success) {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.data.response,
          timestamp: new Date()
        }
        setMessages(prev => [...prev, assistantMessage])

        if (response.data.session_id) {
          setSessionId(response.data.session_id)
        }
      } else {
        message.error('回复失败，请稍后重试')
      }
    } catch (error) {
      console.error('Chat error:', error)
      message.error('网络错误，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    setMessages([])
    setSessionId(null)
    message.success('对话已清空')
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div style={{ height: 'calc(100vh - 200px)', display: 'flex', flexDirection: 'column' }}>
      <Card
        title={
          <Space>
            <RobotOutlined />
            智能问答助手
          </Space>
        }
        extra={
          <Button icon={<ClearOutlined />} onClick={handleClear}>
            清空对话
          </Button>
        }
        style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
        bodyStyle={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
      >
        <div className="chat-messages" style={{ flex: 1, overflowY: 'auto' }}>
          {messages.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#999', padding: 40 }}>
              <RobotOutlined style={{ fontSize: 48, marginBottom: 16 }} />
              <p>您好！我是舆情分析助手，可以帮您：</p>
              <div style={{ marginTop: 16 }}>
                <Tag style={{ margin: 4 }}>查询舆情动态</Tag>
                <Tag style={{ margin: 4 }}>分析舆情趋势</Tag>
                <Tag style={{ margin: 4 }}>生成舆情简报</Tag>
                <Tag style={{ margin: 4 }}>搜索相关信息</Tag>
              </div>
            </div>
          ) : (
            messages.map(msg => (
              <div key={msg.id} className={`chat-message ${msg.role}`}>
                <Avatar
                  icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                  style={{
                    backgroundColor: msg.role === 'user' ? '#1890ff' : '#52c41a'
                  }}
                />
                <div className="message-content">
                  {msg.role === 'assistant' ? (
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  ) : (
                    msg.content
                  )}
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="chat-message assistant">
              <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#52c41a' }} />
              <div className="message-content">
                <Spin size="small" /> 思考中...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div style={{ marginTop: 16 }}>
          <TextArea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入您的问题... (Shift+Enter换行，Enter发送)"
            autoSize={{ minRows: 2, maxRows: 4 }}
            disabled={loading}
          />
          <div style={{ marginTop: 8, textAlign: 'right' }}>
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              loading={loading}
              disabled={!input.trim()}
            >
              发送
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
