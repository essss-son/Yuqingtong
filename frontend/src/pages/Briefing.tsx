import { useState } from 'react'
import { Input, Button, Card, Spin, message, Row, Col, Tag, List, Divider, Empty, Typography } from 'antd'
import { FileTextOutlined, ClockCircleOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
// import ReactMarkdown from 'react-markdown'
import dayjs from 'dayjs'
import { briefingAPI, BriefingData } from '../services/api'

const { Title, Paragraph } = Typography

export default function Briefing() {
  const [loading, setLoading] = useState(false)
  const [topic, setTopic] = useState('')
  const [briefing, setBriefing] = useState<BriefingData | null>(null)

  const handleGenerate = async () => {
    if (!topic.trim()) {
      message.warning('请输入简报主题')
      return
    }

    setLoading(true)
    try {
      const result = await briefingAPI.generate(topic, 24)
      setBriefing(result)
      message.success('简报生成成功')
    } catch (error) {
      message.error('简报生成失败')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const getSentimentChartOption = () => {
    if (!briefing?.sentiment_distribution) return {}
    const data = Object.entries(briefing.sentiment_distribution).map(([name, value]) => ({
      name: name === 'positive' ? '正面' : name === 'negative' ? '负面' : '中性',
      value
    }))
    return {
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: '60%',
        data,
        itemStyle: {
          color: (params: any) => {
            const colors: Record<string, string> = {
              '正面': '#52c41a',
              '负面': '#ff4d4f',
              '中性': '#faad14'
            }
            return colors[params.name] || '#1890ff'
          }
        }
      }]
    }
  }

  const getSourceChartOption = () => {
    if (!briefing?.source_distribution) return {}
    const data = Object.entries(briefing.source_distribution)
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      xAxis: { type: 'category', data: data.map(d => d[0]) },
      yAxis: { type: 'value' },
      series: [{
        data: data.map(d => d[1]),
        type: 'bar',
        itemStyle: { color: '#1890ff' }
      }]
    }
  }

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col flex="auto">
            <Input
              size="large"
              placeholder="输入简报主题，如：某公司舆情"
              value={topic}
              onChange={e => setTopic(e.target.value)}
              prefix={<FileTextOutlined />}
            />
          </Col>
          <Col>
            <Button
              type="primary"
              size="large"
              onClick={handleGenerate}
              loading={loading}
            >
              生成简报
            </Button>
          </Col>
        </Row>
      </Card>

      {loading ? (
        <div className="loading-container">
          <Spin size="large" tip="正在生成简报..." />
        </div>
      ) : briefing ? (
        <div>
          <Card>
            <Title level={3}>{briefing.topic} - 舆情简报</Title>
            <Paragraph type="secondary">
              <ClockCircleOutlined /> 生成时间：{dayjs(briefing.generated_at).format('YYYY-MM-DD HH:mm:ss')}
              <Divider type="vertical" />
              统计周期：最近 {briefing.time_range} 小时
            </Paragraph>
            <Divider />
            <Title level={4}>摘要</Title>
            <Paragraph>{briefing.summary}</Paragraph>
          </Card>

          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col xs={24} lg={12}>
              <Card title="情感分布">
                <ReactECharts option={getSentimentChartOption()} style={{ height: 250 }} />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="来源分布">
                <ReactECharts option={getSourceChartOption()} style={{ height: 250 }} />
              </Card>
            </Col>
          </Row>

          <Card title="热词分析" style={{ marginTop: 16 }}>
            {briefing.hot_keywords?.length > 0 ? (
              <div>
                {briefing.hot_keywords.map((keyword, index) => (
                  <Tag
                    key={index}
                    color={index < 3 ? 'red' : index < 6 ? 'orange' : 'blue'}
                    style={{ margin: 4, fontSize: index < 3 ? 16 : 14 }}
                  >
                    {keyword}
                  </Tag>
                ))}
              </div>
            ) : (
              <Empty description="暂无热词数据" />
            )}
          </Card>

          {briefing.sections?.map((section: any, index: number) => (
            <Card
              key={index}
              title={section.title}
              style={{ marginTop: 16 }}
              className="briefing-section"
            >
              <Paragraph>{section.content}</Paragraph>
              {section.items?.length > 0 && (
                <List
                  dataSource={section.items}
                  renderItem={(item: any) => (
                    <List.Item>
                      <List.Item.Meta
                        title={item.title}
                        description={item.content?.slice(0, 200)}
                      />
                    </List.Item>
                  )}
                />
              )}
            </Card>
          ))}
        </div>
      ) : (
        <Empty
          description="输入主题并点击生成简报"
          style={{ marginTop: 100 }}
        />
      )}
    </div>
  )
}
